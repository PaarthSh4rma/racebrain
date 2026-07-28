import httpx
import pytest
from fastapi.testclient import TestClient

from app.config import get_cors_allowed_origins
from app.data_sources.openf1_client import OpenF1Client, OpenF1Error
from app.main import app


client = TestClient(app)


def generation_payload(**overrides):
    payload = {
        "track": "monaco",
        "total_laps": 20,
        "simulations": 8,
        "include_one_stop": True,
        "include_two_stop": False,
        "seed": 42,
    }
    payload.update(overrides)
    return payload


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "online"


def test_application_imports_without_openrouter_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    assert app.title == "RaceBrain API"


def test_valid_and_invalid_track_lookup():
    valid = client.get("/tracks/monaco")
    assert valid.status_code == 200
    assert valid.json()["name"] == "Monaco"

    invalid = client.get("/tracks/not-a-track")
    assert invalid.status_code == 404
    assert invalid.json()["detail"] == "Unsupported track: not-a-track"


def test_generation_uses_track_defaults_when_overrides_omitted():
    response = client.post("/monte-carlo/generate", json=generation_payload())
    assert response.status_code == 200
    data = response.json()
    assert data["base_lap_time"] == 74.5
    assert data["pit_loss"] == 20.5


def test_generation_uses_user_overrides():
    response = client.post(
        "/monte-carlo/generate",
        json=generation_payload(base_lap_time=88.0, pit_loss=30.0),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["base_lap_time"] == 88.0
    assert data["pit_loss"] == 30.0


def test_generation_validation_limits():
    assert client.post(
        "/monte-carlo/generate", json=generation_payload(simulations=201)
    ).status_code == 422
    assert client.post(
        "/monte-carlo/generate", json=generation_payload(base_lap_time=1)
    ).status_code == 422
    assert client.post(
        "/monte-carlo/generate",
        json=generation_payload(include_one_stop=False, include_two_stop=False),
    ).status_code == 422


def test_cors_configuration_requires_explicit_origins(monkeypatch):
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://app.example.com/")
    assert get_cors_allowed_origins() == ["https://app.example.com"]

    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "*")
    with pytest.raises(ValueError, match="explicit origins"):
        get_cors_allowed_origins()


def test_scenario_rejects_unknown_track():
    response = client.post(
        "/ai/scenario",
        json={
            "question": "What if degradation increases?",
            "track": "not-a-track",
            "total_laps": 20,
            "simulations": 8,
            "original_result": {},
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Unsupported track: not-a-track"


def test_seeded_generation_is_reproducible_and_structured():
    first = client.post("/monte-carlo/generate", json=generation_payload(seed=8675309))
    second = client.post("/monte-carlo/generate", json=generation_payload(seed=8675309))
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()

    data = first.json()
    assert data["seed"] == 8675309
    assert data["best_strategy"] in data["ranked_strategies"]
    assert data["simulations_per_strategy"] == 8
    assert {"confidence", "recommendation", "safety_car_rate"} <= data.keys()


def test_monte_carlo_preferences_are_not_degenerate_for_monaco():
    response = client.post(
        "/monte-carlo/generate",
        json=generation_payload(simulations=200, seed=42),
    )
    assert response.status_code == 200
    ranked = response.json()["ranked_strategies"]
    preferences = [item["preference_percentage"] for item in ranked]

    assert 0 < preferences[0] < 100
    assert sum(value > 0 for value in preferences) > 1
    assert round(sum(preferences), 6) == 100
    assert "sampled scenarios" in response.json()["recommendation"]


def test_openf1_client_builds_expected_request(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return [{"session_key": 123}]

    captured = {}

    def fake_get(url, params, timeout):
        captured.update(url=url, params=params, timeout=timeout)
        return Response()

    monkeypatch.setattr(httpx, "get", fake_get)
    result = OpenF1Client().get_sessions(year=2024, country_name="Monaco", session_name="Race")
    assert result == [{"session_key": 123}]
    assert captured["url"].endswith("/sessions")
    assert captured["params"]["country_name"] == "Monaco"


def test_openf1_client_wraps_upstream_errors(monkeypatch):
    def fail(*args, **kwargs):
        raise httpx.ConnectError("private upstream detail")

    monkeypatch.setattr(httpx, "get", fail)
    try:
        OpenF1Client().get_drivers(123)
    except OpenF1Error as exc:
        assert str(exc) == "OpenF1 race data is temporarily unavailable."
    else:
        raise AssertionError("OpenF1Error was not raised")


def test_race_data_endpoint_returns_safe_upstream_error(monkeypatch):
    from app.api import race_data

    def fail(*args, **kwargs):
        raise OpenF1Error("OpenF1 race data is temporarily unavailable.")

    monkeypatch.setattr(race_data.client, "get_sessions", fail)
    response = client.get("/race-data/sessions?year=2024")
    assert response.status_code == 502
    assert response.json()["detail"] == "OpenF1 race data is temporarily unavailable."


def test_llm_unavailable_returns_503(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    response = client.post(
        "/ai/llm-explain",
        json={
            "question": "Why?",
            "simulation_result": {
                "confidence": "low",
                "win_gap_to_second": 1,
                "best_strategy": {"strategy_id": 1, "win_percentage": 51},
                "ranked_strategies": [],
                "safety_car_rate": 0,
            },
        },
    )
    assert response.status_code == 503
    assert "OPENROUTER_API_KEY" in response.json()["detail"]
