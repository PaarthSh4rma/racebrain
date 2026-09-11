"""Typed results for representative clean-lap pace fitting."""

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from .base import FrozenDomainModel
from .enums import LapExclusionReason, LapQualityWarning, PaceAvailabilityReason
from .estimates import ModelVersion, PaceEstimate
from .identity import CompetitorId
from .modelling import FitDiagnostics, _as_utc


class HardExclusionCount(FrozenDomainModel):
    reason: LapExclusionReason
    lap_count: int = Field(ge=1)


class WarningExclusionCount(FrozenDomainModel):
    warning: LapQualityWarning
    lap_count: int = Field(ge=1)


class PaceSelectionAudit(FrozenDomainModel):
    hard_exclusions: tuple[HardExclusionCount, ...] = ()
    warning_exclusions: tuple[WarningExclusionCount, ...] = ()

    @model_validator(mode="after")
    def reasons_are_unique_and_ordered(self):
        hard = tuple(item.reason for item in self.hard_exclusions)
        warnings = tuple(item.warning for item in self.warning_exclusions)
        if len(hard) != len(set(hard)) or len(warnings) != len(set(warnings)):
            raise ValueError("selection audit reasons must be unique")
        if hard != tuple(reason for reason in LapExclusionReason if reason in hard):
            raise ValueError("hard exclusion audit must use canonical enum ordering")
        if warnings != tuple(reason for reason in LapQualityWarning if reason in warnings):
            raise ValueError("warning exclusion audit must use canonical enum ordering")
        return self


class CompetitorPaceFit(FrozenDomainModel):
    competitor_id: CompetitorId
    estimate: PaceEstimate | None = None
    diagnostics: FitDiagnostics
    selection_audit: PaceSelectionAudit = PaceSelectionAudit()
    unavailable_reason: PaceAvailabilityReason | None = None

    @model_validator(mode="after")
    def result_is_consistent(self):
        if (self.estimate is None) == (self.unavailable_reason is None):
            raise ValueError("pace fit requires exactly one of estimate or unavailable_reason")
        if self.diagnostics.competitor_id != self.competitor_id:
            raise ValueError("diagnostics subject must match pace-fit subject")
        if self.estimate is not None:
            if self.estimate.competitor_id != self.competitor_id:
                raise ValueError("estimate subject must match pace-fit subject")
            if self.estimate.as_of != self.diagnostics.as_of:
                raise ValueError("estimate and diagnostics must use the same cutoff")
            if self.estimate.model_version != self.diagnostics.model_version:
                raise ValueError("estimate and diagnostics must use the same model version")
            if self.estimate.sample_count != self.diagnostics.included_laps:
                raise ValueError("estimate sample count must equal included diagnostic laps")
        return self


class FieldPaceResult(FrozenDomainModel):
    as_of: datetime
    model_version: ModelVersion
    competitors: tuple[CompetitorPaceFit, ...] = Field(min_length=1)

    @field_validator("as_of")
    @classmethod
    def cutoff_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value, "as_of")

    @model_validator(mode="after")
    def competitors_are_unique_ordered_and_versioned(self):
        ids = tuple(item.competitor_id for item in self.competitors)
        if len(ids) != len(set(ids)):
            raise ValueError("field pace subjects must be unique")
        if ids != tuple(sorted(ids, key=str)):
            raise ValueError("field pace subjects require canonical identity ordering")
        if any(item.diagnostics.as_of != self.as_of for item in self.competitors):
            raise ValueError("all field pace diagnostics must use the result cutoff")
        if any(item.diagnostics.model_version != self.model_version for item in self.competitors):
            raise ValueError("all field pace diagnostics must use the result model version")
        return self
