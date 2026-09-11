"""Typed results for empirical within-stint tyre-age pace fitting."""

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from .base import FrozenDomainModel
from .enums import TyreCompound, TyreSlopeAvailabilityReason
from .estimates import ModelVersion, TyreDegradationEstimate
from .identity import CompetitorId
from .modelling import FitDiagnostics, _as_utc
from .pace import PaceSelectionAudit


class TyreSlopeDiagnostics(FitDiagnostics):
    compound: TyreCompound | None = None
    stint_number: int | None = Field(default=None, ge=1)
    minimum_tyre_age_laps: int | None = Field(default=None, ge=0)
    maximum_tyre_age_laps: int | None = Field(default=None, ge=0)
    tyre_age_span_laps: int | None = Field(default=None, ge=0)
    intercept_s: float | None = None

    @model_validator(mode="after")
    def tyre_range_is_consistent(self):
        values = (self.minimum_tyre_age_laps, self.maximum_tyre_age_laps, self.tyre_age_span_laps)
        if any(value is None for value in values) and not all(value is None for value in values):
            raise ValueError("tyre-age diagnostic range must be wholly present or absent")
        if all(value is not None for value in values):
            if self.minimum_tyre_age_laps > self.maximum_tyre_age_laps:
                raise ValueError("minimum tyre age cannot exceed maximum tyre age")
            if self.tyre_age_span_laps != self.maximum_tyre_age_laps - self.minimum_tyre_age_laps:
                raise ValueError("tyre-age span must equal maximum minus minimum age")
        return self


class CompetitorTyreSlopeFit(FrozenDomainModel):
    competitor_id: CompetitorId
    estimate: TyreDegradationEstimate | None = None
    diagnostics: TyreSlopeDiagnostics
    selection_audit: PaceSelectionAudit = PaceSelectionAudit()
    unavailable_reason: TyreSlopeAvailabilityReason | None = None

    @model_validator(mode="after")
    def result_is_consistent(self):
        if (self.estimate is None) == (self.unavailable_reason is None):
            raise ValueError("tyre-slope fit requires exactly one of estimate or unavailable_reason")
        if self.diagnostics.competitor_id != self.competitor_id:
            raise ValueError("diagnostics subject must match tyre-slope subject")
        if self.estimate is not None:
            if self.estimate.competitor_id != self.competitor_id:
                raise ValueError("estimate subject must match tyre-slope subject")
            if self.estimate.as_of != self.diagnostics.as_of:
                raise ValueError("estimate and diagnostics must use the same cutoff")
            if self.estimate.model_version != self.diagnostics.model_version:
                raise ValueError("estimate and diagnostics must use the same model version")
            if self.estimate.sample_count != self.diagnostics.included_laps:
                raise ValueError("estimate sample count must equal included diagnostic laps")
            if self.estimate.compound != self.diagnostics.compound:
                raise ValueError("estimate and diagnostics must use the same compound")
            if self.estimate.stint_number != self.diagnostics.stint_number:
                raise ValueError("estimate and diagnostics must use the same bounded stint")
            if (
                self.estimate.minimum_tyre_age_laps != self.diagnostics.minimum_tyre_age_laps
                or self.estimate.maximum_tyre_age_laps != self.diagnostics.maximum_tyre_age_laps
            ):
                raise ValueError("estimate and diagnostics must use the same tyre-age range")
        return self


class FieldTyreSlopeResult(FrozenDomainModel):
    as_of: datetime
    model_version: ModelVersion
    competitors: tuple[CompetitorTyreSlopeFit, ...] = Field(min_length=1)

    @field_validator("as_of")
    @classmethod
    def cutoff_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value, "as_of")

    @model_validator(mode="after")
    def competitors_are_unique_ordered_and_versioned(self):
        ids = tuple(item.competitor_id for item in self.competitors)
        if len(ids) != len(set(ids)):
            raise ValueError("field tyre-slope subjects must be unique")
        if ids != tuple(sorted(ids, key=str)):
            raise ValueError("field tyre-slope subjects require canonical identity ordering")
        if any(item.diagnostics.as_of != self.as_of for item in self.competitors):
            raise ValueError("all field tyre-slope diagnostics must use the result cutoff")
        if any(item.diagnostics.model_version != self.model_version for item in self.competitors):
            raise ValueError("all field tyre-slope diagnostics must use the result model version")
        return self
