"""Explicit public API contracts for the V2 historical workbench."""

from pydantic import BaseModel, ConfigDict, Field

from app.domain_v2.race_state import RaceState


class HistoricalSessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    session_key: int
    meeting_key: int
    year: int
    event_name: str
    country_name: str
    location: str
    session_name: str
    session_type: str | None = None


class HistoricalDriverSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    driver_number: int
    full_name: str
    name_acronym: str | None = None
    team_name: str | None = None


class DecisionLapSummary(BaseModel):
    session_key: int
    driver_number: int
    laps: tuple[int, ...]


class HistoricalRaceStateApiRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    session_key: int = Field(gt=0)
    driver_number: int = Field(gt=0)
    decision_lap: int = Field(gt=0)


class ReconstructionDiagnosticsResponse(BaseModel):
    malformed_records: int
    future_records: int
    untimed_records: int
    duplicate_records: int
    excluded_competitors: int
    foreign_session_records: int
    bounded_pit_lane_passages: int
    included_records: dict[str, int]
    cache_hits: dict[str, bool]


class HistoricalRaceStateResponse(BaseModel):
    race_state: RaceState
    diagnostics: ReconstructionDiagnosticsResponse
