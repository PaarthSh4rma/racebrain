"""Canonical provider-independent race-state contracts."""

from datetime import datetime, timezone

from pydantic import Field, field_validator, model_validator

from .base import FrozenDomainModel
from .enums import TrackStatus
from .identity import CompetitorId, DriverId, EventId, SessionId
from .provenance import DataQuality, ExternalIdentifier, Provenance
from .timing import Gap
from .tyre import TyreSetState


class Event(FrozenDomainModel):
    event_id: EventId
    name: str = Field(min_length=1)
    circuit_id: str | None = None
    external_ids: tuple[ExternalIdentifier, ...] = ()


class Session(FrozenDomainModel):
    session_id: SessionId
    event: Event
    name: str = Field(min_length=1)
    scheduled_laps: int | None = Field(default=None, ge=1)
    external_ids: tuple[ExternalIdentifier, ...] = ()


class WeatherState(FrozenDomainModel):
    observed_at: datetime
    air_temperature_c: float | None = Field(default=None, ge=-50.0, le=80.0)
    track_temperature_c: float | None = Field(default=None, ge=-50.0, le=100.0)
    humidity_fraction: float | None = Field(default=None, ge=0.0, le=1.0)
    wind_speed_mps: float | None = Field(default=None, ge=0.0)
    rainfall_detected: bool | None = None
    provenance: tuple[Provenance, ...] = ()

    @field_validator("observed_at")
    @classmethod
    def observed_time_is_utc(cls, value: datetime):
        return _as_utc(value, "observed_at")


class LapObservation(FrozenDomainModel):
    lap_number: int = Field(ge=1)
    lap_time_s: float = Field(gt=0.0)
    completed_at: datetime
    is_pit_in_lap: bool | None = None
    is_pit_out_lap: bool | None = None

    @field_validator("completed_at")
    @classmethod
    def completion_must_be_utc(cls, value: datetime):
        return _as_utc(value, "completed_at")


class TrackStatusState(FrozenDomainModel):
    status: TrackStatus
    observed_at: datetime
    provenance: tuple[Provenance, ...] = ()

    @field_validator("observed_at")
    @classmethod
    def observed_time_is_utc(cls, value: datetime):
        return _as_utc(value, "observed_at")


class CarState(FrozenDomainModel):
    """State of a competitive session entry, not a physical chassis."""

    competitor_id: CompetitorId
    observed_at: datetime
    driver_id: DriverId | None = None
    driver_name: str | None = None
    position: int | None = Field(default=None, ge=1)
    current_lap: int | None = Field(default=None, ge=0)
    gap_ahead: Gap | None = None
    gap_behind: Gap | None = None
    gap_to_leader: Gap | None = None
    tyre: TyreSetState | None = None
    recent_laps: tuple[LapObservation, ...] = ()
    in_pit: bool | None = None
    pit_stop_count: int | None = Field(default=None, ge=0)
    data_quality: DataQuality = DataQuality()
    provenance: tuple[Provenance, ...] = ()
    external_ids: tuple[ExternalIdentifier, ...] = ()

    @field_validator("observed_at")
    @classmethod
    def observed_time_is_utc(cls, value: datetime):
        return _as_utc(value, "observed_at")

    @model_validator(mode="after")
    def laps_do_not_postdate_competitor_state(self):
        if any(lap.completed_at > self.observed_at for lap in self.recent_laps):
            raise ValueError("lap completion cannot postdate enclosing competitor state")
        return self


class RaceState(FrozenDomainModel):
    session: Session
    observation_cutoff: datetime
    track_status: TrackStatusState | None = None
    weather: WeatherState | None = None
    competitors: tuple[CarState, ...] = Field(min_length=1)
    data_quality: DataQuality = DataQuality()
    provenance: tuple[Provenance, ...] = ()

    @field_validator("observation_cutoff")
    @classmethod
    def cutoff_must_be_utc(cls, value: datetime):
        return _as_utc(value, "observation_cutoff")

    @model_validator(mode="after")
    def competitors_have_unique_domain_ids(self):
        ids = [competitor.competitor_id for competitor in self.competitors]
        if len(ids) != len(set(ids)):
            raise ValueError("competitor_id must be unique within a race state")
        if any(item.observed_at > self.observation_cutoff for item in self.competitors):
            raise ValueError("competitor state cannot postdate race-state cutoff")
        if any(lap.completed_at > self.observation_cutoff for item in self.competitors for lap in item.recent_laps):
            raise ValueError("race state cannot contain observations after its cutoff")
        if self.weather is not None and self.weather.observed_at > self.observation_cutoff:
            raise ValueError("weather cannot postdate race-state cutoff")
        if self.track_status is not None and self.track_status.observed_at > self.observation_cutoff:
            raise ValueError("track status cannot postdate race-state cutoff")
        return self


def _as_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be a usable timezone-aware timestamp")
    return value.astimezone(timezone.utc)
