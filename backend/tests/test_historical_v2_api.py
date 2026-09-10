from copy import deepcopy

from fastapi.testclient import TestClient

from app.api import historical_v2
from app.data_sources.openf1_client import OpenF1Error
from app.main import app
from tests.fixtures.openf1_v2_fixtures import historical_payload

api = TestClient(app)


def install_payload(monkeypatch, payload=None):
    payload = deepcopy(payload or historical_payload())
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


def test_session_driver_and_decision_lap_discovery(monkeypatch):
    install_payload(monkeypatch)
    sessions = api.get("/v2/historical/sessions?year=2024")
    assert sessions.status_code == 200
    assert sessions.json() == [{
        "session_key": 999, "meeting_key": 88, "year": 2024,
        "event_name": "Monaco Grand Prix", "country_name": "Monaco",
        "location": "Monaco", "session_name": "Race", "session_type": "Race",
    }]
    drivers = api.get("/v2/historical/sessions/999/drivers")
    assert drivers.status_code == 200
    assert {item["driver_number"] for item in drivers.json()} == {4, 16, 77}
    laps = api.get("/v2/historical/sessions/999/drivers/16/decision-laps")
    assert laps.status_code == 200
    assert laps.json()["laps"] == [1, 2]


def test_successful_race_state_serializes_canonical_semantics(monkeypatch):
    install_payload(monkeypatch)
    response = api.post("/v2/historical/race-state", json={"session_key": 999, "driver_number": 16, "decision_lap": 2})
    assert response.status_code == 200
    body = response.json()
    state = body["race_state"]
    assert state["observation_cutoff"] == "2024-05-26T13:02:00Z"
    assert sorted(car["current_lap"] for car in state["competitors"]) == [1, 2]
    leader = next(car for car in state["competitors"] if car["position"] == 1)
    second = next(car for car in state["competitors"] if car["position"] == 2)
    assert leader["gap_ahead"] is None
    assert leader["gap_to_leader"] == {"seconds": 0.0, "laps": None}
    assert second["gap_to_leader"] == {"seconds": None, "laps": 1}
    assert leader["pit_stop_count"] is None and leader["in_pit"] is None
    assert state["data_quality"]["level"] == "degraded"
    assert leader["provenance"]


def test_invalid_requests_and_typed_failures_are_operator_readable(monkeypatch):
    payload = install_payload(monkeypatch)
    assert api.post("/v2/historical/race-state", json={"session_key": 0, "driver_number": 16, "decision_lap": 2}).status_code == 422
    payload["laps"][1]["date_start"] = None
    cutoff = api.post("/v2/historical/race-state", json={"session_key": 999, "driver_number": 16, "decision_lap": 2})
    assert cutoff.status_code == 422
    assert "timed focal lap" in cutoff.json()["detail"]

    payload["laps"][1]["date_start"] = "2024-05-26T13:01:00Z"
    payload["drivers"] = [item for item in payload["drivers"] if item["driver_number"] != 16]
    missing = api.post("/v2/historical/race-state", json={"session_key": 999, "driver_number": 16, "decision_lap": 2})
    assert missing.status_code == 404
    assert "focal driver" in missing.json()["detail"]


def test_discovery_and_reconstruction_upstream_failures_are_502(monkeypatch):
    def unavailable(*args, **kwargs):
        raise OpenF1Error("private URL https://provider.invalid?token=secret")

    monkeypatch.setattr(historical_v2.client, "get_sessions", unavailable)
    discovery = api.get("/v2/historical/sessions?year=2024")
    reconstruction = api.post("/v2/historical/race-state", json={"session_key": 999, "driver_number": 16, "decision_lap": 2})
    assert discovery.status_code == reconstruction.status_code == 502
    assert discovery.json()["detail"] == "Historical data provider is temporarily unavailable."
    assert reconstruction.json()["detail"] == "Historical data provider is temporarily unavailable."
    assert "provider.invalid" not in discovery.text + reconstruction.text
    assert "secret" not in discovery.text + reconstruction.text


def test_malformed_discovery_payload_is_safe_502(monkeypatch):
    monkeypatch.setattr(historical_v2.client, "get_sessions", lambda **kwargs: {"unexpected": "object"})
    monkeypatch.setattr(historical_v2.client, "get_meetings", lambda **kwargs: [])
    response = api.get("/v2/historical/sessions?year=2024")
    assert response.status_code == 502
    assert response.json()["detail"] == "Historical session data could not be loaded."


def test_malformed_driver_and_lap_payloads_have_stable_categories(monkeypatch):
    monkeypatch.setattr(historical_v2.client, "get_drivers", lambda *args: {"private": "driver payload"})
    drivers = api.get("/v2/historical/sessions/999/drivers")
    laps = api.get("/v2/historical/sessions/999/drivers/16/decision-laps")
    assert drivers.status_code == laps.status_code == 502
    assert drivers.json()["detail"] == "Historical driver data could not be loaded."
    assert laps.json()["detail"] == "Historical decision-lap data could not be loaded."

    install_payload(monkeypatch)
    monkeypatch.setattr(historical_v2.client, "get_laps", lambda *args: {"private": "lap payload"})
    laps = api.get("/v2/historical/sessions/999/drivers/16/decision-laps")
    assert laps.status_code == 502
    assert laps.json()["detail"] == "Historical decision-lap data could not be loaded."


def test_unexpected_reconstruction_failure_is_sanitized(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("private implementation detail")

    monkeypatch.setattr(historical_v2, "reconstruct_historical_race_state", fail)
    response = api.post("/v2/historical/race-state", json={"session_key": 999, "driver_number": 16, "decision_lap": 2})
    assert response.status_code == 500
    assert response.json()["detail"] == "Historical race state could not be reconstructed."
    assert "private" not in response.text


def test_unknown_driver_and_empty_lap_discovery(monkeypatch):
    payload = install_payload(monkeypatch)
    unknown = api.get("/v2/historical/sessions/999/drivers/44/decision-laps")
    assert unknown.status_code == 404
    payload["laps"] = []
    empty = api.get("/v2/historical/sessions/999/drivers/16/decision-laps")
    assert empty.status_code == 404
    assert "No defensible" in empty.json()["detail"]


def test_v1_replay_route_remains_registered():
    paths = {route.path for route in app.routes}
    assert "/replay/sessions" in paths
    assert "/v2/historical/race-state" in paths
