import httpx
import pytest
from fastapi.testclient import TestClient

from app.data_sources.openf1_client import MemoryTTLCache, OpenF1Client, OpenF1Error
from app.main import app
from app.models.replay import ReplayRequest
from app.services import replay_service
from tests.fixtures.replay_fixtures import (
    CHANGING_WEATHER_RACE,
    DRY_RACE,
    INCOMPLETE_DATA_RACE,
    MULTIPLE_STINT_RACE,
    SAFETY_CAR_RACE,
    clone_case,
)

api = TestClient(app)


def install_case(monkeypatch, case):
    fixture = clone_case(case)
    monkeypatch.setattr(replay_service.client, "get_sessions", lambda **kwargs: fixture["sessions"])
    monkeypatch.setattr(replay_service.client, "get_drivers", lambda *args, **kwargs: fixture["drivers"])
    monkeypatch.setattr(replay_service.client, "get_laps", lambda *args, **kwargs: fixture["laps"])
    monkeypatch.setattr(replay_service.client, "get_stints", lambda *args, **kwargs: fixture["stints"])
    monkeypatch.setattr(replay_service.client, "get_weather", lambda *args, **kwargs: fixture["weather"])
    monkeypatch.setattr(
        replay_service.client,
        "get_race_control",
        lambda *args, **kwargs: fixture["race_control"],
    )
    replay_service.client.last_cache_hit = False
    return fixture


def request(lap=6, **overrides):
    values = {
        "session_key": 9523,
        "driver_number": 1,
        "decision_lap": lap,
        "seed": 77,
        "simulations": 40,
    }
    values.update(overrides)
    return ReplayRequest(**values)


def test_snapshot_bounds_laps_weather_and_future_events(monkeypatch):
    install_case(monkeypatch, SAFETY_CAR_RACE)
    snapshot = replay_service.build_replay_snapshot(request(lap=6))
    assert max(lap.lap_number for lap in snapshot.bounded_laps) == 6
    assert snapshot.data_quality.records["laps"].ignored_future == 6
    assert snapshot.race_control.safety_car_events == 0
    assert snapshot.race_control.red_flag_events == 0
    assert snapshot.data_quality.records["race_control"].ignored_future == 2
    assert snapshot.data_quality.records["weather"].ignored_future > 0
    assert snapshot.available_decision_laps == [1, 2, 3, 4, 5, 6]
    assert snapshot.session.date_end is None
    decision = next(lap for lap in snapshot.bounded_laps if lap.lap_number == 6)
    assert snapshot.cutoff_timestamp == decision.date_start + replay_service.timedelta(
        seconds=decision.lap_duration
    )
    assert all(
        sample <= snapshot.cutoff_timestamp
        for sample in [snapshot.data_quality.latest_included_timestamp]
        if sample is not None
    )


def test_current_stint_and_tyre_age_use_bounded_information(monkeypatch):
    install_case(monkeypatch, MULTIPLE_STINT_RACE)
    lap_six = replay_service.build_replay_snapshot(request(lap=6))
    assert lap_six.current_stint.stint_number == 1
    assert lap_six.current_stint.lap_end == 6
    assert lap_six.estimated_tyre_age == 6
    assert all(stint.lap_start <= 6 for stint in lap_six.bounded_stints)

    lap_eight = replay_service.build_replay_snapshot(request(lap=8))
    assert lap_eight.current_stint.stint_number == 2
    assert lap_eight.estimated_tyre_age == 2


def test_ended_stint_is_not_presented_as_current(monkeypatch):
    case = clone_case(DRY_RACE)
    case["stints"] = [case["stints"][0]]
    case["stints"][0]["lap_end"] = 4
    install_case(monkeypatch, case)
    snapshot = replay_service.build_replay_snapshot(request(lap=6))
    assert snapshot.current_stint is None
    assert snapshot.current_compound is None
    assert snapshot.estimated_tyre_age is None
    assert any("No valid stint" in warning for warning in snapshot.data_quality.warnings)


def test_future_weather_does_not_create_hindsight_rain(monkeypatch):
    install_case(monkeypatch, CHANGING_WEATHER_RACE)
    snapshot = replay_service.build_replay_snapshot(request(lap=5))
    assert snapshot.weather.rainfall_detected is False
    assert snapshot.data_quality.records["weather"].ignored_future >= 1


def test_out_of_order_duplicates_and_mixed_timezone_data_are_normalised(monkeypatch):
    case = clone_case(CHANGING_WEATHER_RACE)
    case["sessions"][0]["date_end"] = "2024-05-26T15:00:00Z"
    case["laps"].append(
        {
            **case["laps"][4],
            "lap_duration": "999.0",
            "date_start": "2024-05-26T13:59:00Z",
        }
    )
    case["weather"].reverse()
    case["race_control"].reverse()
    case["weather"].append(
        {
            "date": "2024-05-26T13:05:00",
            "air_temperature": "",
            "rainfall": "0",
        }
    )
    fixture = install_case(monkeypatch, case)
    snapshot = replay_service.build_replay_snapshot(request(lap=5))
    assert len([lap for lap in snapshot.bounded_laps if lap.lap_number == 5]) == 1
    assert snapshot.bounded_laps[-1].lap_duration != 999.0
    assert snapshot.weather.rainfall_detected is False
    assert snapshot.race_control.red_flag_events == 0
    assert snapshot.session.date_end is None
    assert any("incomplete or malformed" in item for item in snapshot.data_quality.warnings)
    assert fixture["weather"][0]["date"] > fixture["weather"][-2]["date"]


def test_missing_lap_timestamp_uses_conservative_lap_number_cutoff(monkeypatch):
    case = clone_case(DRY_RACE)
    case["laps"][5]["date_start"] = None
    install_case(monkeypatch, case)
    snapshot = replay_service.build_replay_snapshot(request(lap=6))
    assert snapshot.cutoff_timestamp is None
    assert snapshot.data_quality.cutoff_source == "lap_number_only"
    assert snapshot.data_quality.records["weather"].included == 0
    assert snapshot.weather.trend == "unknown"
    assert any("timestamp-only context" in item for item in snapshot.data_quality.warnings)


def test_invalid_decision_lap_unknown_session_and_driver(monkeypatch):
    install_case(monkeypatch, DRY_RACE)
    with pytest.raises(replay_service.ReplayValidationError, match="completed laps"):
        replay_service.build_replay_snapshot(request(lap=99))

    monkeypatch.setattr(replay_service.client, "get_sessions", lambda **kwargs: [])
    with pytest.raises(replay_service.ReplayValidationError, match="Unknown historical session"):
        replay_service.build_replay_snapshot(request())

    install_case(monkeypatch, DRY_RACE)
    with pytest.raises(replay_service.ReplayValidationError, match="Unknown driver"):
        replay_service.build_replay_snapshot(request(driver_number=44))


def test_incomplete_data_returns_explicit_warnings(monkeypatch):
    install_case(monkeypatch, INCOMPLETE_DATA_RACE)
    snapshot = replay_service.build_replay_snapshot(request(lap=6))
    assert snapshot.data_quality.warnings
    assert any("incomplete" in warning for warning in snapshot.data_quality.warnings)


def test_deterministic_recommendation_and_safety_car_behavior(monkeypatch):
    install_case(monkeypatch, SAFETY_CAR_RACE)
    snapshot = replay_service.build_replay_snapshot(request(lap=8))
    first = replay_service.recommend_strategy(snapshot)
    second = replay_service.recommend_strategy(snapshot)
    assert first == second
    assert snapshot.race_control.safety_car_active is True
    assert first.recommendation == "keep_flexible"


def test_seeded_alternatives_reproduce_and_share_sampled_conditions(monkeypatch):
    install_case(monkeypatch, DRY_RACE)
    first = replay_service.build_replay_assessment(request(lap=8, seed=123))
    second = replay_service.build_replay_assessment(request(lap=8, seed=123))
    assert first.alternatives == second.alternatives
    assert first.recommended_alternative == second.recommended_alternative
    assert {item.alternative for item in first.alternatives} == {
        "pit_now",
        "extend",
        "hold",
    }
    assert all(item.uncertainty >= 0 for item in first.alternatives)


def test_each_simulation_samples_conditions_once_for_all_alternatives(monkeypatch):
    install_case(monkeypatch, DRY_RACE)
    snapshot = replay_service.build_replay_snapshot(request(lap=8))
    calls = []

    class RecordingRandom:
        def __init__(self, seed):
            self.seed = seed

        def gauss(self, mean, standard_deviation):
            calls.append((mean, standard_deviation))
            return mean

    monkeypatch.setattr(replay_service.random, "Random", RecordingRandom)
    replay_service.compare_alternatives(
        snapshot,
        replay_service.recommend_strategy(snapshot),
        extend_laps=5,
        simulations=10,
        seed=123,
    )
    assert len(calls) == 20


def test_endpoint_schemas_and_validation(monkeypatch):
    fixture = install_case(monkeypatch, DRY_RACE)
    fixture["sessions"].append(fixture["sessions"][0].copy())
    fixture["drivers"].append(fixture["drivers"][0].copy())
    payload = request(lap=6).model_dump()
    assert len(api.get("/replay/sessions?year=2024").json()) == 1
    assert len(api.get("/replay/sessions/9523/drivers").json()) == 1
    response = api.post("/replay/assessment", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["snapshot"]["decision_lap"] == 6
    assert body["recommendation"]["recommendation"]
    assert len(body["alternatives"]) == 3

    invalid = api.post("/replay/snapshot", json={**payload, "decision_lap": 99})
    assert invalid.status_code == 422
    assert "completed laps" in invalid.json()["detail"]


def test_upstream_failure_is_safe(monkeypatch):
    def fail(**kwargs):
        raise OpenF1Error("OpenF1 race data is temporarily unavailable.")

    monkeypatch.setattr(replay_service.client, "get_sessions", fail)
    response = api.post("/replay/snapshot", json=request().model_dump())
    assert response.status_code == 502
    assert response.json()["detail"] == "OpenF1 race data is temporarily unavailable."


def test_cache_hit_and_clear(monkeypatch):
    calls = 0

    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return [{"session_key": 9523}]

    def fake_get(*args, **kwargs):
        nonlocal calls
        calls += 1
        return Response()

    monkeypatch.setattr(httpx, "get", fake_get)
    cached_client = OpenF1Client()
    assert cached_client.get_sessions(session_key=9523) == [{"session_key": 9523}]
    assert cached_client.last_cache_hit is False
    assert cached_client.get_sessions(session_key=9523) == [{"session_key": 9523}]
    assert cached_client.last_cache_hit is True
    assert calls == 1
    cached_client.clear_cache()
    cached_client.get_sessions(session_key=9523)
    assert calls == 2


def test_cache_isolates_keys_values_and_expiry(monkeypatch):
    calls = []
    clock = 100.0

    class Response:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return [{"year": len(calls)}]

    def fake_get(url, params, timeout):
        calls.append(dict(params))
        return Response()

    monkeypatch.setattr(httpx, "get", fake_get)
    monkeypatch.setattr(
        "app.data_sources.openf1_client.time.monotonic",
        lambda: clock,
    )
    cached_client = OpenF1Client()
    first = cached_client.get_sessions(year=2023)
    first[0]["year"] = 0
    assert cached_client.get_sessions(year=2023) == [{"year": 1}]
    assert cached_client.get_sessions(year=2024) == [{"year": 2}]
    assert calls == [{"year": 2023}, {"year": 2024}]

    clock = 1000.0
    assert cached_client.get_sessions(year=2023) == [{"year": 3}]
    assert len(calls) == 3

    bounded_cache = MemoryTTLCache(max_size=1)
    bounded_cache.set(("first",), [1], ttl=10)
    bounded_cache.set(("second",), [2], ttl=10)
    assert bounded_cache.get(("first",)) is None
    assert bounded_cache.get(("second",)) == [2]


def test_transient_failures_retry_but_permanent_4xx_does_not(monkeypatch):
    attempts = 0

    class Success:
        status_code = 200

        def raise_for_status(self):
            return None

        def json(self):
            return []

    def transient(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise httpx.ConnectError("temporary")
        return Success()

    monkeypatch.setattr(httpx, "get", transient)
    assert OpenF1Client(retries=2).get_sessions(year=2024) == []
    assert attempts == 3

    attempts = 0

    def permanent(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        request_object = httpx.Request("GET", "https://api.openf1.org/v1/sessions")
        response = httpx.Response(404, request=request_object)
        raise httpx.HTTPStatusError("not found", request=request_object, response=response)

    monkeypatch.setattr(httpx, "get", permanent)
    with pytest.raises(OpenF1Error):
        OpenF1Client(retries=2).get_sessions(year=2024)
    assert attempts == 1
