"""Controlled vocabulary for RaceBrain V2."""

from enum import Enum


class StrEnum(str, Enum):
    pass


class TrackStatus(StrEnum):
    UNKNOWN = "unknown"
    GREEN = "green"
    YELLOW = "yellow"
    VSC = "virtual_safety_car"
    SAFETY_CAR = "safety_car"
    RED = "red_flag"


class TyreCompound(StrEnum):
    SOFT = "soft"
    MEDIUM = "medium"
    HARD = "hard"
    INTERMEDIATE = "intermediate"
    WET = "wet"
    UNKNOWN = "unknown"


class DataQualityLevel(StrEnum):
    GOOD = "good"
    DEGRADED = "degraded"
    INSUFFICIENT = "insufficient"
    UNKNOWN = "unknown"


class ConfidenceLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"


class DistributionKind(StrEnum):
    NORMAL = "normal"
    QUANTILE = "quantile"
    BOUNDED = "bounded"


class TriggerMetric(StrEnum):
    GAP_AHEAD_S = "gap_ahead_s"
    GAP_BEHIND_S = "gap_behind_s"
    INTERVAL_TO_COMPETITOR_S = "interval_to_competitor_s"
    DEGRADATION_S_PER_LAP = "degradation_s_per_lap"
    PACE_DELTA_S_PER_LAP = "pace_delta_s_per_lap"
    PIT_LOSS_S = "pit_loss_s"
    REJOIN_MARGIN_S = "rejoin_margin_s"
    TYRE_AGE_LAPS = "tyre_age_laps"
    RAIN_CROSSOVER_LAPS = "rain_crossover_laps"
    TRACK_STATUS = "track_status"


class StrategyActionType(StrEnum):
    STAY_OUT = "stay_out"
    PIT_NOW = "pit_now"
    PIT_TARGET = "pit_target"
    RECONSIDER = "reconsider"


class TriggerOperator(StrEnum):
    EQ = "eq"
    NE = "ne"
    GT = "gt"
    GTE = "gte"
    LT = "lt"
    LTE = "lte"
    CHANGES_TO = "changes_to"


class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNKNOWN = "unknown"
