"""Canonical provider-independent race-state contracts."""

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from .base import FrozenDomainModel
from .enums import TrackStatus
from .identity import CompetitorId, DriverId, EventId, SessionId
from .provenance import DataQuality, ExternalIdentifier, Provenance
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
    air_temperature_c: float | None = Field(default=None, ge=-50.0, le=80.0)
    track_temperature_c: float | None = Field(default=None, ge=-50.0, le=100.0)
    humidity_fraction: float | None = Field(default=None, ge=0.0, le=1.0)
    wind_speed_mps: float | None = Field(default=None, ge=0.0)
    rainfall_detected: bool | None = None
    provenance: tuple[Provenance, ...] = ()


class LapObservation(FrozenDomainModel):
    lap_number: int = Field(ge=1)
    lap_time_s: float = Field(gt=0.0)
    completed_at: datetime | None = None
    is_pit_in_lap: bool | None = None
    is_pit_out_lap: bool | None = None

    @field_validator("completed_at")
    @classmethod
    def completion_must_be_aware(cls, value: datetime | None):
        if value is not None and value.tzinfo is None:
            raise ValueError("completed_at must include a timezone")
        return value


class CarState(FrozenDomainModel):
    """State of a competitive session entry, not a physical chassis."""

    competitor_id: CompetitorId
    driver_id: DriverId | None = None
    driver_name: str | None = None
    position: int | None = Field(default=None, ge=1)
    current_lap: int | None = Field(default=None, ge=0)
    gap_ahead_s: float | None = Field(default=None, ge=0.0)
    gap_behind_s: float | None = Field(default=None, ge=0.0)
    interval_to_leader_s: float | None = Field(default=None, ge=0.0)
    tyre: TyreSetState | None = None
    recent_laps: tuple[LapObservation, ...] = ()
    in_pit: bool | None = None
    pit_stop_count: int | None = Field(default=None, ge=0)
    data_quality: DataQuality = DataQuality()
    provenance: tuple[Provenance, ...] = ()
    external_ids: tuple[ExternalIdentifier, ...] = ()


class RaceState(FrozenDomainModel):
    session: Session
    session_lap: int | None = Field(default=None, ge=1)
    observation_cutoff: datetime
    track_status: TrackStatus = TrackStatus.UNKNOWN
    weather: WeatherState | None = None
    competitors: tuple[CarState, ...] = Field(min_length=1)
    data_quality: DataQuality = DataQuality()
    provenance: tuple[Provenance, ...] = ()

    @field_validator("observation_cutoff")
    @classmethod
    def cutoff_must_be_aware(cls, value: datetime):
        if value.tzinfo is None:
            raise ValueError("observation_cutoff must include a timezone")
        return value

    @model_validator(mode="after")
    def competitors_have_unique_domain_ids(self):
        ids = [competitor.competitor_id for competitor in self.competitors]
        if len(ids) != len(set(ids)):
            raise ValueError("competitor_id must be unique within a race state")
        if any(
            lap.completed_at is not None and lap.completed_at > self.observation_cutoff
            for competitor in self.competitors
            for lap in competitor.recent_laps
        ):
            raise ValueError("race state cannot contain observations after its cutoff")
        return self
