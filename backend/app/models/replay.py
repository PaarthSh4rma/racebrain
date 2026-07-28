from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TolerantModel(BaseModel):
    model_config = ConfigDict(extra="ignore")

    @field_validator("*", mode="before")
    @classmethod
    def empty_strings_are_missing(cls, value):
        return None if value == "" else value

    @field_validator("date_start", "date_end", "date", check_fields=False)
    @classmethod
    def timestamps_are_utc(cls, value: datetime | None):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)


class HistoricalSession(TolerantModel):
    session_key: int
    session_name: str = "Race"
    session_type: str | None = None
    country_name: str | None = None
    circuit_short_name: str | None = None
    location: str | None = None
    year: int | None = None
    date_start: datetime | None = None
    date_end: datetime | None = None


class DriverSummary(TolerantModel):
    driver_number: int
    broadcast_name: str | None = None
    full_name: str | None = None
    name_acronym: str | None = None
    team_name: str | None = None
    team_colour: str | None = None


class LapRecord(TolerantModel):
    session_key: int | None = None
    driver_number: int | None = None
    lap_number: int
    lap_duration: float | None = None
    date_start: datetime | None = None
    is_pit_out_lap: bool | None = None


class StintRecord(TolerantModel):
    session_key: int | None = None
    driver_number: int | None = None
    stint_number: int | None = None
    lap_start: int
    lap_end: int | None = None
    compound: str | None = None
    tyre_age_at_start: int | None = None


class WeatherSample(TolerantModel):
    date: datetime | None = None
    air_temperature: float | None = None
    track_temperature: float | None = None
    humidity: float | None = None
    wind_speed: float | None = None
    rainfall: float | int | bool | None = None


class RaceControlEvent(TolerantModel):
    date: datetime | None = None
    lap_number: int | None = None
    category: str | None = None
    flag: str | None = None
    message: str | None = None


class ReplayRequest(BaseModel):
    session_key: int = Field(gt=0)
    driver_number: int = Field(gt=0, le=999)
    decision_lap: int = Field(gt=0, le=200)
    seed: int | None = None
    extend_laps: int = Field(default=5, ge=1, le=15)
    simulations: int = Field(default=120, ge=10, le=500)


class DecisionLapAvailability(BaseModel):
    session_key: int
    driver_number: int
    laps: list[int]


class RecordCount(BaseModel):
    included: int = 0
    ignored_future: int = 0


class ReplayDataQuality(BaseModel):
    cutoff_source: Literal["lap_completion_timestamp", "lap_number_only"]
    latest_included_timestamp: datetime | None = None
    records: dict[str, RecordCount]
    warnings: list[str] = Field(default_factory=list)
    cache_hits: dict[str, bool] = Field(default_factory=dict)


class PaceSummary(BaseModel):
    recent_lap_times: list[float]
    recent_average: float | None
    previous_average: float | None
    trend_seconds_per_lap: float | None
    trend: Literal["improving", "stable", "degrading", "unknown"]


class WeatherSummary(BaseModel):
    air_temperature: float | None = None
    track_temperature: float | None = None
    humidity: float | None = None
    wind_speed: float | None = None
    rainfall_detected: bool = False
    trend: Literal["dry", "rain_detected", "unknown"] = "unknown"


class RaceControlSummary(BaseModel):
    safety_car_active: bool = False
    red_flag_active: bool = False
    safety_car_events: int = 0
    red_flag_events: int = 0
    recent_messages: list[str] = Field(default_factory=list)


class ReplaySnapshot(BaseModel):
    session: HistoricalSession
    driver: DriverSummary
    decision_lap: int
    available_decision_laps: list[int]
    cutoff_timestamp: datetime | None
    current_stint: StintRecord | None
    current_compound: str | None
    estimated_tyre_age: int | None
    pace: PaceSummary
    weather: WeatherSummary
    race_control: RaceControlSummary
    bounded_laps: list[LapRecord]
    bounded_stints: list[StintRecord]
    data_quality: ReplayDataQuality


class StrategyRecommendation(BaseModel):
    recommendation: Literal[
        "hold",
        "extend",
        "pit_window_opening",
        "box_now",
        "keep_flexible",
        "monitor_weather",
        "preserve_tyres",
        "attack",
    ]
    confidence: Literal["low", "medium", "high"]
    summary: str
    tyre_risk: Literal["low", "medium", "high", "unknown"]
    reasoning_factors: list[str]
    evidence: dict[str, float | int | str | bool | None]
    limitations: list[str]


class AlternativeStrategyComparison(BaseModel):
    alternative: Literal["pit_now", "extend", "hold"]
    strategy_score: float
    delta_to_recommended: float
    uncertainty: float
    tyre_risk: Literal["low", "medium", "high", "unknown"]
    explanation: str


class ReplayAssessment(BaseModel):
    snapshot: ReplaySnapshot
    recommendation: StrategyRecommendation
    alternatives: list[AlternativeStrategyComparison]
    recommended_alternative: Literal["pit_now", "extend", "hold"]
    seed: int | None
    simulations: int
