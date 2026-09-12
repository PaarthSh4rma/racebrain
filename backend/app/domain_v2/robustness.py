"""Typed, non-probabilistic diagnostics for accepted V2.2 point models."""

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from .base import FrozenDomainModel
from .enums import PaceQuantileMethod, RobustnessAvailabilityReason, SlopeSign
from .estimates import EmpiricalQuantiles, ModelVersion, StatisticalInterval, _provenance_is_bounded
from .identity import CompetitorId
from .modelling import _as_utc
from .pace import CompetitorPaceFit
from .provenance import DataQuality, Provenance
from .tyre_slope import CompetitorTyreSlopeFit


TYRE_SLOPE_SENSITIVITY_METHOD = "leave-one-observation-out deterministic sensitivity envelope"


class PaceRobustnessDiagnostics(FrozenDomainModel):
    quantile_method: PaceQuantileMethod
    quantiles: EmpiricalQuantiles
    minimum_lap_time_s: float = Field(gt=0.0)
    maximum_lap_time_s: float = Field(gt=0.0)
    p90_p10_spread_s: float = Field(ge=0.0)

    @model_validator(mode="after")
    def empirical_values_reconcile(self):
        if self.minimum_lap_time_s > self.maximum_lap_time_s:
            raise ValueError("minimum lap time cannot exceed maximum lap time")
        if not (
            self.minimum_lap_time_s
            <= self.quantiles.p10
            <= self.quantiles.p90
            <= self.maximum_lap_time_s
        ):
            raise ValueError("pace quantiles must remain inside the empirical lap-time range")
        if self.p90_p10_spread_s != self.quantiles.p90 - self.quantiles.p10:
            raise ValueError("pace empirical spread must equal p90 minus p10")
        return self


class PaceRobustnessResult(FrozenDomainModel):
    competitor_id: CompetitorId
    as_of: datetime
    point_model_version: ModelVersion
    robustness_model_version: ModelVersion
    point_fit: CompetitorPaceFit
    diagnostics: PaceRobustnessDiagnostics | None = None
    unavailable_reason: RobustnessAvailabilityReason | None = None
    data_quality: DataQuality
    provenance: tuple[Provenance, ...] = ()
    limitations: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def cutoff_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value, "as_of")

    @model_validator(mode="after")
    def result_reconciles_with_point_fit(self):
        if (self.diagnostics is None) == (self.unavailable_reason is None):
            raise ValueError("pace robustness requires exactly one of diagnostics or unavailable_reason")
        if self.point_fit.competitor_id != self.competitor_id:
            raise ValueError("pace robustness subject must match its point fit")
        if self.point_fit.diagnostics.as_of != self.as_of:
            raise ValueError("pace robustness cutoff must match its point fit")
        if self.point_fit.diagnostics.model_version != self.point_model_version:
            raise ValueError("pace robustness point version must match its point fit")
        point_quality = (
            self.point_fit.estimate.data_quality
            if self.point_fit.estimate
            else self.point_fit.diagnostics.data_quality
        )
        if self.data_quality != point_quality or self.data_quality.completeness is not None:
            raise ValueError("pace robustness must preserve point-fit DataQuality with unknown completeness")
        if self.point_fit.estimate is None:
            if self.unavailable_reason is not RobustnessAvailabilityReason.POINT_ESTIMATE_UNAVAILABLE:
                raise ValueError("unavailable pace point fits require unavailable robustness")
        else:
            if self.diagnostics is None:
                raise ValueError("available pace point fits require robustness diagnostics")
            if self.diagnostics.quantiles.sample_count != self.point_fit.estimate.sample_count:
                raise ValueError("pace robustness sample count must match its point estimate")
            if self.diagnostics.quantiles.p50 != self.point_fit.estimate.value:
                raise ValueError("pace robustness p50 must equal its point estimate")
        _provenance_is_bounded(self.provenance, self.as_of, "pace robustness")
        return self


class FieldPaceRobustnessResult(FrozenDomainModel):
    as_of: datetime
    point_model_version: ModelVersion
    robustness_model_version: ModelVersion
    competitors: tuple[PaceRobustnessResult, ...] = Field(min_length=1)

    @field_validator("as_of")
    @classmethod
    def cutoff_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value, "as_of")

    @model_validator(mode="after")
    def competitors_are_canonical(self):
        ids = tuple(item.competitor_id for item in self.competitors)
        if len(ids) != len(set(ids)) or ids != tuple(sorted(ids, key=str)):
            raise ValueError("field pace robustness subjects must be unique and canonically ordered")
        if any(item.as_of != self.as_of for item in self.competitors):
            raise ValueError("all field pace robustness results must use the field cutoff")
        if any(item.point_model_version != self.point_model_version for item in self.competitors):
            raise ValueError("all field pace robustness results must use the point model version")
        if any(item.robustness_model_version != self.robustness_model_version for item in self.competitors):
            raise ValueError("all field pace robustness results must use the robustness model version")
        return self


class LeaveOneOutSlope(FrozenDomainModel):
    omitted_lap_number: int = Field(ge=1)
    slope_s_per_lap_per_lap: float
    sign: SlopeSign


class SlopeSignCounts(FrozenDomainModel):
    negative: int = Field(ge=0)
    zero: int = Field(ge=0)
    positive: int = Field(ge=0)


class TyreSlopeRobustnessDiagnostics(FrozenDomainModel):
    nominal_slope_s_per_lap_per_lap: float
    nominal_sign: SlopeSign
    zero_tolerance_s_per_lap_per_lap: float = Field(ge=0.0)
    leave_one_out_refits: tuple[LeaveOneOutSlope, ...] = Field(min_length=1)
    leave_one_out_refit_count: int = Field(ge=1)
    leave_one_out_min_s_per_lap_per_lap: float
    leave_one_out_max_s_per_lap_per_lap: float
    sensitivity_envelope: StatisticalInterval
    sign_stable: bool
    sign_counts: SlopeSignCounts
    maximum_absolute_deviation_s_per_lap_per_lap: float = Field(ge=0.0)
    most_influential_omitted_lap: int = Field(ge=1)

    @model_validator(mode="after")
    def diagnostics_reconcile(self):
        laps = tuple(item.omitted_lap_number for item in self.leave_one_out_refits)
        if len(laps) != len(set(laps)) or laps != tuple(sorted(laps)):
            raise ValueError("leave-one-out refits require unique canonical lap ordering")
        slopes = tuple(item.slope_s_per_lap_per_lap for item in self.leave_one_out_refits)
        if self.leave_one_out_refit_count != len(slopes):
            raise ValueError("leave-one-out refit count must match recorded refits")
        if self.leave_one_out_min_s_per_lap_per_lap != min(slopes):
            raise ValueError("leave-one-out minimum must match recorded refits")
        if self.leave_one_out_max_s_per_lap_per_lap != max(slopes):
            raise ValueError("leave-one-out maximum must match recorded refits")
        if self.nominal_sign is not _classify_sign(
            self.nominal_slope_s_per_lap_per_lap, self.zero_tolerance_s_per_lap_per_lap
        ):
            raise ValueError("nominal sign must use the explicit zero tolerance")
        if any(
            item.sign is not _classify_sign(item.slope_s_per_lap_per_lap, self.zero_tolerance_s_per_lap_per_lap)
            for item in self.leave_one_out_refits
        ):
            raise ValueError("refit signs must use the explicit zero tolerance")
        if self.sensitivity_envelope.coverage is not None:
            raise ValueError("deterministic sensitivity envelope cannot declare coverage")
        if self.sensitivity_envelope.method != TYRE_SLOPE_SENSITIVITY_METHOD:
            raise ValueError("tyre robustness requires the deterministic leave-one-out sensitivity method")
        if self.sensitivity_envelope.lower != min(self.nominal_slope_s_per_lap_per_lap, *slopes):
            raise ValueError("sensitivity lower bound must contain nominal and all refits")
        if self.sensitivity_envelope.upper != max(self.nominal_slope_s_per_lap_per_lap, *slopes):
            raise ValueError("sensitivity upper bound must contain nominal and all refits")
        counted = {
            SlopeSign.NEGATIVE: self.sign_counts.negative,
            SlopeSign.ZERO: self.sign_counts.zero,
            SlopeSign.POSITIVE: self.sign_counts.positive,
        }
        if any(counted[sign] != sum(item.sign is sign for item in self.leave_one_out_refits) for sign in SlopeSign):
            raise ValueError("slope sign counts must match leave-one-out refits")
        if sum(counted.values()) != self.leave_one_out_refit_count:
            raise ValueError("slope sign counts must equal leave-one-out refit count")
        if self.sign_stable != all(item.sign is self.nominal_sign for item in self.leave_one_out_refits):
            raise ValueError("sign stability must compare every refit sign with the nominal sign")
        deviations = tuple(abs(value - self.nominal_slope_s_per_lap_per_lap) for value in slopes)
        if self.maximum_absolute_deviation_s_per_lap_per_lap != max(deviations):
            raise ValueError("maximum absolute deviation must match recorded refits")
        influential = min(
            item.omitted_lap_number
            for item, deviation in zip(self.leave_one_out_refits, deviations)
            if deviation == self.maximum_absolute_deviation_s_per_lap_per_lap
        )
        if self.most_influential_omitted_lap != influential:
            raise ValueError("most influential omission must use lowest-lap tie-breaking")
        return self


class TyreSlopeRobustnessResult(FrozenDomainModel):
    competitor_id: CompetitorId
    as_of: datetime
    point_model_version: ModelVersion
    robustness_model_version: ModelVersion
    point_fit: CompetitorTyreSlopeFit
    diagnostics: TyreSlopeRobustnessDiagnostics | None = None
    unavailable_reason: RobustnessAvailabilityReason | None = None
    data_quality: DataQuality
    provenance: tuple[Provenance, ...] = ()
    limitations: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def cutoff_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value, "as_of")

    @model_validator(mode="after")
    def result_reconciles_with_point_fit(self):
        if (self.diagnostics is None) == (self.unavailable_reason is None):
            raise ValueError("tyre robustness requires exactly one of diagnostics or unavailable_reason")
        if self.point_fit.competitor_id != self.competitor_id:
            raise ValueError("tyre robustness subject must match its point fit")
        if self.point_fit.diagnostics.as_of != self.as_of:
            raise ValueError("tyre robustness cutoff must match its point fit")
        if self.point_fit.diagnostics.model_version != self.point_model_version:
            raise ValueError("tyre robustness point version must match its point fit")
        point_quality = (
            self.point_fit.estimate.data_quality
            if self.point_fit.estimate
            else self.point_fit.diagnostics.data_quality
        )
        if self.data_quality != point_quality or self.data_quality.completeness is not None:
            raise ValueError("tyre robustness must preserve point-fit DataQuality with unknown completeness")
        if self.point_fit.estimate is None:
            if self.unavailable_reason is not RobustnessAvailabilityReason.POINT_ESTIMATE_UNAVAILABLE:
                raise ValueError("unavailable tyre point fits require unavailable robustness")
        elif self.diagnostics is not None:
            if self.diagnostics.nominal_slope_s_per_lap_per_lap != self.point_fit.estimate.value:
                raise ValueError("tyre robustness nominal slope must equal its point estimate")
            if self.diagnostics.leave_one_out_refit_count != self.point_fit.estimate.sample_count:
                raise ValueError("tyre robustness must omit each accepted observation exactly once")
        elif self.unavailable_reason is not RobustnessAvailabilityReason.INVALID_DIAGNOSTIC_REFIT:
            raise ValueError("available tyre point fits may lack diagnostics only for invalid refits")
        _provenance_is_bounded(self.provenance, self.as_of, "tyre robustness")
        return self


class FieldTyreSlopeRobustnessResult(FrozenDomainModel):
    as_of: datetime
    point_model_version: ModelVersion
    robustness_model_version: ModelVersion
    competitors: tuple[TyreSlopeRobustnessResult, ...] = Field(min_length=1)

    @field_validator("as_of")
    @classmethod
    def cutoff_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value, "as_of")

    @model_validator(mode="after")
    def competitors_are_canonical(self):
        ids = tuple(item.competitor_id for item in self.competitors)
        if len(ids) != len(set(ids)) or ids != tuple(sorted(ids, key=str)):
            raise ValueError("field tyre robustness subjects must be unique and canonically ordered")
        if any(item.as_of != self.as_of for item in self.competitors):
            raise ValueError("all field tyre robustness results must use the field cutoff")
        if any(item.point_model_version != self.point_model_version for item in self.competitors):
            raise ValueError("all field tyre robustness results must use the point model version")
        if any(item.robustness_model_version != self.robustness_model_version for item in self.competitors):
            raise ValueError("all field tyre robustness results must use the robustness model version")
        return self


def _classify_sign(slope: float, tolerance: float) -> SlopeSign:
    if slope > tolerance:
        return SlopeSign.POSITIVE
    if slope < -tolerance:
        return SlopeSign.NEGATIVE
    return SlopeSign.ZERO
