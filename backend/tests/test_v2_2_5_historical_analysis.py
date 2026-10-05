from copy import deepcopy
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.api import historical_v2
from app.application_v2 import analyze_historical
from app.application_v2.analyze_historical import analyze_historical_decision_point
from app.application_v2.reconstruct_race_state import HistoricalRaceStateRequest
from app.data_sources.openf1_client import OpenF1Error
from app.domain_v2.enums import RobustnessAvailabilityReason, SlopeSign
from app.main import app
from app.models_v2.model_robustness import BASELINE_ROBUSTNESS_CONFIG
from app.models_v2.representative_pace import BASELINE_PACE_CONFIG
from app.models_v2.tyre_age_slope import BASELINE_TYRE_SLOPE_CONFIG
from tests.fixtures.openf1_v2_fixtures import RecordingOpenF1Client, historical_payload


api = TestClient(app)


def analysis_payload():
    payload = historical_payload()
    start = datetime(2024, 5, 26, 13, 0, tzinfo=timezone.utc)
    payload["laps"] = [
        {
            "session_key": 999,
            "driver_number": driver,
            "lap_number": lap,
            "date_start": (start + timedelta(seconds=(lap - 1) * 82 + offset)).isoformat(),
            "lap_duration": 79.0 + lap * slope + offset / 10,
        }
        for driver, offset, slope in ((16, 0, 0.12), (4, 1, -0.04))
        for lap in range(1, 9)
    ]
    payload["positions"] = [
        {"session_key": 999, "driver_number": 16, "date": "2024-05-26T13:10:00Z", "position": 1},
        {"session_key": 999, "driver_number": 4, "date": "2024-05-26T13:10:00Z", "position": 2},
    ]
    payload["intervals"] = [
        {"session_key": 999, "driver_number": 16, "date": "2024-05-26T13:10:00Z", "interval": 0.0, "gap_to_leader": 0.0},
        {"session_key": 999, "driver_number": 4, "date": "2024-05-26T13:10:00Z", "interval": 1.25, "gap_to_leader": 1.25},
    ]
    payload["weather"] = [payload["weather"][0]]
    payload["race_control"] = [payload["race_control"][0]]
    return payload


def request(lap=8):
    return HistoricalRaceStateRequest(
        openf1_session_key=999,
        focal_driver_number=16,
        decision_lap=lap,
    )


def install_payload(monkeypatch, payload=None):
    payload = deepcopy(payload or analysis_payload())
    methods = {
        "get_sessions": "sessions",
        "get_meetings": "meetings",
        "get_drivers": "drivers",
        "get_laps": "laps",
        "get_stints": "stints",
        "get_intervals": "intervals",
        "get_position": "positions",
        "get_pit": "pits",
        "get_weather": "weather",
        "get_race_control": "race_control",
    }
    for method, key in methods.items():
        monkeypatch.setattr(historical_v2.client, method, lambda *args, _key=key, **kwargs: payload[_key])
    historical_v2.client.last_cache_hit = False
    return payload


def test_application_builds_one_context_and_runs_real_full_field_models(monkeypatch):
    client = RecordingOpenF1Client(analysis_payload())
    calls = 0
    original = analyze_historical.build_historical_pace_context

    def counted(*args, **kwargs):
        nonlocal calls
        calls += 1
        return original(*args, **kwargs)

    monkeypatch.setattr(analyze_historical, "build_historical_pace_context", counted)
    result = analyze_historical_decision_point(request(), client)

    assert calls == 1
    assert result.pace.as_of == result.tyre_age_slope.as_of == result.race_state.observation_cutoff
    canonical = tuple(sorted((car.competitor_id for car in result.race_state.competitors), key=str))
    assert tuple(item.competitor_id for item in result.pace.competitors) == canonical
    assert tuple(item.competitor_id for item in result.tyre_age_slope.competitors) == canonical
    assert all(item.point_fit.estimate is not None for item in result.pace.competitors)
    assert all(item.point_fit.estimate is not None for item in result.tyre_age_slope.competitors)
    assert result.pace.point_model_version == BASELINE_PACE_CONFIG.version()
    assert result.tyre_age_slope.point_model_version == BASELINE_TYRE_SLOPE_CONFIG.version()
    assert result.pace.robustness_model_version == BASELINE_ROBUSTNESS_CONFIG.version()
    assert result.tyre_age_slope.robustness_model_version == BASELINE_ROBUSTNESS_CONFIG.version()
    assert all(item.data_quality == item.point_fit.estimate.data_quality for item in result.pace.competitors)
    assert all(item.diagnostics.nominal_sign in SlopeSign for item in result.tyre_age_slope.competitors)
    assert result.evidence[0].pace.included_laps == tuple(range(2, 9))
    assert result.evidence[0].pace.excluded_laps[0].lap_number == 1


def test_analysis_preserves_unavailable_results_instead_of_fabricating_values():
    result = analyze_historical_decision_point(request(lap=2), RecordingOpenF1Client(historical_payload()))
    assert all(item.point_fit.estimate is None for item in result.pace.competitors)
    assert all(item.unavailable_reason is RobustnessAvailabilityReason.POINT_ESTIMATE_UNAVAILABLE for item in result.pace.competitors)
    assert all(item.point_fit.estimate is None for item in result.tyre_age_slope.competitors)
    assert all(item.point_fit.unavailable_reason is not None for item in result.tyre_age_slope.competitors)


def test_future_provider_rows_do_not_contaminate_historical_analysis():
    baseline = analysis_payload()
    contaminated = deepcopy(baseline)
    contaminated["laps"].append({
        "session_key": 999,
        "driver_number": 16,
        "lap_number": 99,
        "date_start": "2024-05-26T18:00:00Z",
        "lap_duration": 20.0,
    })
    before = analyze_historical_decision_point(request(), RecordingOpenF1Client(baseline))
    after = analyze_historical_decision_point(request(), RecordingOpenF1Client(contaminated))
    assert after.race_state == before.race_state
    assert after.pace == before.pace
    assert after.tyre_age_slope == before.tyre_age_slope
    assert after.modelling_diagnostics.rows_bounded_out > before.modelling_diagnostics.rows_bounded_out


def test_analysis_endpoint_serializes_typed_aggregate_and_keeps_race_state_route(monkeypatch):
    install_payload(monkeypatch)
    response = api.post("/v2/historical/analysis", json={"session_key": 999, "driver_number": 16, "decision_lap": 8})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "race_state", "reconstruction_diagnostics", "modelling_diagnostics", "pace", "tyre_age_slope", "evidence",
    }
    cutoff = body["race_state"]["observation_cutoff"]
    assert body["pace"]["as_of"] == body["tyre_age_slope"]["as_of"] == cutoff
    canonical = sorted(car["competitor_id"] for car in body["race_state"]["competitors"])
    assert [item["competitor_id"] for item in body["pace"]["competitors"]] == canonical
    assert [item["competitor_id"] for item in body["tyre_age_slope"]["competitors"]] == canonical
    assert body["pace"]["point_model_version"]["config_hash"] == BASELINE_PACE_CONFIG.version().config_hash
    assert body["tyre_age_slope"]["point_model_version"]["config_hash"] == BASELINE_TYRE_SLOPE_CONFIG.version().config_hash
    assert body["pace"]["robustness_model_version"]["config_hash"] == BASELINE_ROBUSTNESS_CONFIG.version().config_hash
    assert body["modelling_diagnostics"]["admitted_observations"] > 0
    assert body["evidence"][0]["pace"]["included_laps"] == list(range(2, 9))

    legacy = api.post("/v2/historical/race-state", json={"session_key": 999, "driver_number": 16, "decision_lap": 8})
    assert legacy.status_code == 200
    assert set(legacy.json()) == {"race_state", "diagnostics"}


def test_analysis_provider_and_malformed_evidence_fail_safely(monkeypatch):
    def unavailable(*args, **kwargs):
        raise OpenF1Error("private provider URL with token=secret")

    monkeypatch.setattr(historical_v2.client, "get_sessions", unavailable)
    provider = api.post("/v2/historical/analysis", json={"session_key": 999, "driver_number": 16, "decision_lap": 8})
    assert provider.status_code == 502
    assert provider.json()["detail"] == "Historical data provider is temporarily unavailable."
    assert "secret" not in provider.text

    install_payload(monkeypatch)
    monkeypatch.setattr(historical_v2.client, "get_laps", lambda *args: {"private": "malformed evidence"})
    malformed = api.post("/v2/historical/analysis", json={"session_key": 999, "driver_number": 16, "decision_lap": 8})
    assert malformed.status_code == 422
    assert "malformed" not in malformed.text
    assert "private" not in malformed.text
