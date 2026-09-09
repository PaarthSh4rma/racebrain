"""Explicit numerical estimate semantics and units."""

from pydantic import Field, model_validator

from .base import FrozenDomainModel
from .enums import ConfidenceLevel, DistributionKind
from .provenance import Provenance
from .identity import CompetitorId


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
        if self.kind == DistributionKind.NORMAL and self.standard_deviation is None:
            raise ValueError("normal uncertainty requires standard_deviation")
        if self.kind == DistributionKind.QUANTILE and self.quantiles is None:
            raise ValueError("quantile uncertainty requires empirical quantiles")
        if self.kind == DistributionKind.BOUNDED and self.interval is None:
            raise ValueError("bounded uncertainty requires an interval")
        if not any((self.interval, self.quantiles, self.standard_deviation is not None)):
            raise ValueError("uncertainty requires an explicit representation")
        return self


class ModelEstimate(FrozenDomainModel):
    value: float
    unit: str = Field(min_length=1)
    model_version: ModelVersion
    uncertainty: Uncertainty | None = None
    confidence: ConfidenceLevel = ConfidenceLevel.UNKNOWN
    assumptions: tuple[str, ...] = ()
    provenance: tuple[Provenance, ...] = ()


class PaceEstimate(ModelEstimate):
    unit: str = Field(default="s/lap", pattern=r"^s/lap$")


class DegradationEstimate(ModelEstimate):
    unit: str = Field(default="s/lap/lap", pattern=r"^s/lap/lap$")


class PitLossEstimate(ModelEstimate):
    unit: str = Field(default="s", pattern=r"^s$")


class RejoinEstimate(FrozenDomainModel):
    expected_position: float | None = Field(default=None, ge=1.0)
    gap_ahead_s: float | None = Field(default=None, ge=0.0)
    gap_behind_s: float | None = Field(default=None, ge=0.0)
    nearby_competitor_ids: tuple[CompetitorId, ...] = ()
    uncertainty: Uncertainty | None = None
    model_version: ModelVersion
    assumptions: tuple[str, ...] = ()
    provenance: tuple[Provenance, ...] = ()
