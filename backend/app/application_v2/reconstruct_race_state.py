"""Application orchestration for OpenF1 historical full-field reconstruction."""

from dataclasses import dataclass, replace

from pydantic import BaseModel, ConfigDict, Field

from app.adapters.openf1_v2.dto import DriverDTO, IntervalDTO, LapDTO, PitDTO, PositionDTO, RaceControlDTO, SessionDTO, StintDTO, WeatherDTO
from app.adapters.openf1_v2.mapper import OpenF1Dataset, ParsedRecords, ReconstructionDiagnostics, reconstruct
from app.data_sources.openf1_client import OpenF1Client
from app.domain_v2.race_state import RaceState


class HistoricalRaceStateRequest(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True)
    openf1_session_key: int = Field(gt=0)
    focal_driver_number: int = Field(gt=0)
    decision_lap: int = Field(gt=0)


@dataclass(frozen=True)
class HistoricalRaceStateResult:
    race_state: RaceState
    diagnostics: ReconstructionDiagnostics


def _parse(raw, model):
    records, malformed = [], 0
    for value in raw:
        try:
            records.append(model.model_validate(value))
        except (ValueError, TypeError):
            malformed += 1
    return ParsedRecords(tuple(records), malformed)


def reconstruct_historical_race_state(request: HistoricalRaceStateRequest, client: OpenF1Client | None = None) -> HistoricalRaceStateResult:
    client = client or OpenF1Client()
    key = request.openf1_session_key
    specs = (
        ("sessions", SessionDTO, lambda: client.get_sessions(session_key=key)),
        ("drivers", DriverDTO, lambda: client.get_drivers(key)),
        ("laps", LapDTO, lambda: client.get_laps(key)),
        ("stints", StintDTO, lambda: client.get_stints(key)),
        ("intervals", IntervalDTO, lambda: client.get_intervals(key)),
        ("positions", PositionDTO, lambda: client.get_position(key)),
        ("pits", PitDTO, lambda: client.get_pit(key)),
        ("weather", WeatherDTO, lambda: client.get_weather(key)),
        ("race_control", RaceControlDTO, lambda: client.get_race_control(key)),
    )
    parsed, cache_hits = {}, {}
    for name, model, fetch in specs:
        parsed[name] = _parse(fetch(), model)
        cache_hits[name] = client.last_cache_hit
    state, diagnostics = reconstruct(OpenF1Dataset(**parsed), key, request.focal_driver_number, request.decision_lap)
    return HistoricalRaceStateResult(state, replace(diagnostics, cache_hits=cache_hits))
