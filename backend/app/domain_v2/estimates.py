"""Explicit numerical estimate semantics and units."""

from datetime import datetime, timezone

from pydantic import Field, field_validator, model_validator

from .base import FrozenDomainModel
from .enums import ConfidenceLevel, DistributionKind, TyreCompound
from .provenance import DataQuality, Provenance
from .identity import CompetitorId
from .timing import Gap


class ModelVersion(FrozenDomainModel):
    model_name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    config_hash: str = Field(min_length=8, max_length=128, pattern=r"^[A-Za-z0-9:_-]+$")


class StatisticalInterval(FrozenDomainModel):
    lower: float
    upper: float
    coverage: float | None = Field(default=None, gt=0.0, lt=1.0)
    method: str = Field(min_length=1)

    @model_validator(mode="after")
    def interval_is_ordered(self):
        if self.lower > self.upper:
            raise ValueError("uncertainty lower bound cannot exceed upper bound")
        return self


class EmpiricalQuantiles(FrozenDomainModel):
    p10: float
    p50: float
    p90: float
    sample_count: int = Field(ge=1)

    @model_validator(mode="after")
    def quantiles_are_ordered(self):
        if not self.p10 <= self.p50 <= self.p90:
            raise ValueError("empirical quantiles must satisfy p10 <= p50 <= p90")
        return self


class ScenarioFrequency(FrozenDomainModel):
    """Descriptive sampled-scenario frequency, not event probability."""

    frequency: float = Field(ge=0.0, le=1.0)
    matching_scenarios: int = Field(ge=0)
    total_scenarios: int = Field(ge=1)

    @model_validator(mode="after")
    def frequency_matches_counts(self):
        if self.matching_scenarios > self.total_scenarios:
            raise ValueError("matching_scenarios cannot exceed total_scenarios")
        expected = self.matching_scenarios / self.total_scenarios
        if abs(self.frequency - expected) > 1e-9:
            raise ValueError("frequency must equal matching_scenarios / total_scenarios")
        return self


class Uncertainty(FrozenDomainModel):
    """Probabilistic/model spread without assuming a Gaussian distribution."""

    kind: DistributionKind
    interval: StatisticalInterval | None = None
    quantiles: EmpiricalQuantiles | None = None
    standard_deviation: float | None = Field(default=None, ge=0.0)

    @model_validator(mode="after")
    def representation_matches_kind(self):
        present = {
            "interval": self.interval is not None,
            "quantiles": self.quantiles is not None,
            "standard_deviation": self.standard_deviation is not None,
        }
        required = {
            DistributionKind.BOUNDED: "interval",
            DistributionKind.QUANTILE: "quantiles",
            DistributionKind.NORMAL: "standard_deviation",
        }[self.kind]
        if not present[required] or sum(present.values()) != 1:
            raise ValueError(f"{self.kind.value} uncertainty requires only {required}")
        return self


class ModelEstimate(FrozenDomainModel):
    value: float
    unit: str = Field(min_length=1)
    model_version: ModelVersion
    uncertainty: Uncertainty | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    assumptions: tuple[str, ...] = ()
    provenance: tuple[Provenance, ...] = ()


class EvidenceWindow(FrozenDomainModel):
    started_at: datetime
    ended_at: datetime
    first_lap: int = Field(ge=1)
    last_lap: int = Field(ge=1)

    @field_validator("started_at", "ended_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime, info) -> datetime:
        return _as_utc(value, info.field_name)

    @model_validator(mode="after")
    def window_is_ordered(self):
        if self.started_at > self.ended_at or self.first_lap > self.last_lap:
            raise ValueError("evidence window must be chronologically ordered")
        return self


class PaceEstimate(ModelEstimate):
    unit: str = Field(default="s/lap", pattern=r"^s/lap$")
    competitor_id: CompetitorId
    as_of: datetime
    sample_count: int = Field(ge=1)
    evidence_window: EvidenceWindow
    data_quality: DataQuality = DataQuality()
    limitations: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def cutoff_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value, "as_of")

    @model_validator(mode="after")
    def representative_pace_is_bounded(self):
        if self.value <= 0:
            raise ValueError("representative clean-lap pace must be strictly positive")
        if self.evidence_window.ended_at > self.as_of:
            raise ValueError("pace evidence cannot postdate the estimate cutoff")
        _provenance_is_bounded(self.provenance, self.as_of, "pace estimate")
        return self


class TyreDegradationEstimate(ModelEstimate):
    unit: str = Field(default="s/lap/lap", pattern=r"^s/lap/lap$")
    competitor_id: CompetitorId
    as_of: datetime
    compound: TyreCompound
    stint_number: int | None = Field(default=None, ge=1)
    minimum_tyre_age_laps: int = Field(ge=0)
    maximum_tyre_age_laps: int = Field(ge=0)
    sample_count: int = Field(ge=2)
    evidence_window: EvidenceWindow
    data_quality: DataQuality = DataQuality()
    limitations: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def cutoff_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value, "as_of")

    @model_validator(mode="after")
    def degradation_evidence_is_bounded(self):
        if self.minimum_tyre_age_laps >= self.maximum_tyre_age_laps:
            raise ValueError("tyre-age slope requires a strictly positive age span")
        if self.evidence_window.ended_at > self.as_of:
            raise ValueError("degradation evidence cannot postdate the estimate cutoff")
        _provenance_is_bounded(self.provenance, self.as_of, "tyre degradation estimate")
        return self


# Retain the architecture-foundation name for existing imports.
DegradationEstimate = TyreDegradationEstimate


class PitLossEstimate(ModelEstimate):
    unit: str = Field(default="s", pattern=r"^s$")


class RaceTimeDeltaEstimate(ModelEstimate):
    """Race-time consequence relative to a stated strategy baseline, in seconds."""

    unit: str = Field(default="s", pattern=r"^s$")


class RejoinEstimate(FrozenDomainModel):
    expected_position: float | None = Field(default=None, ge=1.0)
    gap_ahead: Gap | None = None
    gap_behind: Gap | None = None
    nearby_competitor_ids: tuple[CompetitorId, ...] = ()
    uncertainty: Uncertainty | None = None
    model_version: ModelVersion
    assumptions: tuple[str, ...] = ()
    provenance: tuple[Provenance, ...] = ()


def _as_utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a usable timezone-aware timestamp")
    return value.astimezone(timezone.utc)


def _provenance_is_bounded(items: tuple[Provenance, ...], cutoff: datetime, owner: str) -> None:
    if any(item.observed_at is not None and item.observed_at > cutoff for item in items):
        raise ValueError(f"{owner} provenance cannot contain source observations after its cutoff")
