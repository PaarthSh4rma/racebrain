"""Tolerant DTOs for the subset of current OpenF1 fields used by V2.1."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from .parsing import empty_to_none, utc_datetime


class OpenF1DTO(BaseModel):
    model_config = ConfigDict(extra="ignore")

    @field_validator("*", mode="before")
    @classmethod
    def blank_is_missing(cls, value: Any) -> Any:
        return empty_to_none(value)


class DatedDTO(OpenF1DTO):
    date: datetime | None = None

    @field_validator("date", mode="before")
    @classmethod
    def parse_date(cls, value: Any) -> datetime | None:
        return utc_datetime(value)


class SessionDTO(OpenF1DTO):
    session_key: int | None = None
    meeting_key: int | None = None
    year: int | None = None
    country_name: str | None = None
    location: str | None = None
    circuit_short_name: str | None = None
    session_name: str | None = None
    session_type: str | None = None


class DriverDTO(OpenF1DTO):
    session_key: int | None = None
    driver_number: int | None = None
    full_name: str | None = None
    first_name: str | None = None
    last_name: str | None = None


class LapDTO(OpenF1DTO):
    session_key: int | None = None
    driver_number: int | None = None
    lap_number: int | None = None
    lap_duration: float | None = None
    date_start: datetime | None = None
    is_pit_out_lap: bool | None = None

    @field_validator("date_start", mode="before")
    @classmethod
    def parse_start(cls, value: Any) -> datetime | None:
        return utc_datetime(value)


class StintDTO(OpenF1DTO):
    session_key: int | None = None
    driver_number: int | None = None
    stint_number: int | None = None
    lap_start: int | None = None
    lap_end: int | None = None
    compound: str | None = None
    tyre_age_at_start: int | None = None


class IntervalDTO(DatedDTO):
    session_key: int | None = None
    driver_number: int | None = None
    interval: Any = None
    gap_to_leader: Any = None


class PositionDTO(DatedDTO):
    session_key: int | None = None
    driver_number: int | None = None
    position: int | None = None


class PitDTO(DatedDTO):
    session_key: int | None = None
    driver_number: int | None = None
    lap_number: int | None = None
    stop_duration: float | None = None
    lane_duration: float | None = None


class WeatherDTO(DatedDTO):
    session_key: int | None = None
    air_temperature: float | None = None
    track_temperature: float | None = None
    humidity: float | None = None
    wind_speed: float | None = None
    rainfall: bool | int | None = None


class RaceControlDTO(DatedDTO):
    session_key: int | None = None
    category: str | None = None
    flag: str | None = None
    message: str | None = None
    scope: str | None = None
