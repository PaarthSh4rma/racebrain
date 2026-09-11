"""Provider-independent contracts for bounded pace and tyre modelling evidence."""

from datetime import datetime, timezone
from hashlib import sha256
import json

from pydantic import Field, field_validator, model_validator

from .base import FrozenDomainModel
from .enums import LapExclusionReason, LapQualityWarning, TrackStatus, TyreCompound
from .estimates import ModelVersion, _provenance_is_bounded
from .identity import CompetitorId
from .provenance import DataQuality, Provenance
from .race_state import RaceState, WeatherState
from .timing import Gap


class GapEvidence(FrozenDomainModel):
    observed_at: datetime
    gap_ahead: Gap | None = None
    gap_to_leader: Gap | None = None
    provenance: tuple[Provenance, ...] = ()

    @field_validator("observed_at")
    @classmethod
    def timestamp_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value, "observed_at")


class TrackStatusEvidence(FrozenDomainModel):
    observed_at: datetime
    status: TrackStatus
    provenance: tuple[Provenance, ...] = ()

    @field_validator("observed_at")
    @classmethod
    def timestamp_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value, "observed_at")


class ModellingLapObservation(FrozenDomainModel):
    competitor_id: CompetitorId
    lap_number: int = Field(ge=1)
    completed_at: datetime
    lap_time_s: float = Field(gt=0.0)
    compound: TyreCompound | None = None
    tyre_age_laps: int | None = Field(default=None, ge=0)
    stint_number: int | None = Field(default=None, ge=1)
    track_status: TrackStatusEvidence | None = None
    weather: WeatherState | None = None
    gap_evidence: GapEvidence | None = None
    hard_exclusions: tuple[LapExclusionReason, ...] = ()
    quality_warnings: tuple[LapQualityWarning, ...] = ()
    data_quality: DataQuality = DataQuality()
    provenance: tuple[Provenance, ...] = ()

    @field_validator("completed_at")
    @classmethod
    def completion_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value, "completed_at")

    @model_validator(mode="after")
    def aligned_evidence_does_not_postdate_lap(self):
        if self.weather is not None and self.weather.observed_at > self.completed_at:
            raise ValueError("weather aligned to a lap cannot postdate its completion")
        if self.gap_evidence is not None and self.gap_evidence.observed_at > self.completed_at:
            raise ValueError("gap evidence aligned to a lap cannot postdate its completion")
        if self.track_status is not None and self.track_status.observed_at > self.completed_at:
            raise ValueError("track status aligned to a lap cannot postdate its completion")
        provenance_groups = (
            self.provenance,
            self.gap_evidence.provenance if self.gap_evidence is not None else (),
            self.track_status.provenance if self.track_status is not None else (),
            self.weather.provenance if self.weather is not None else (),
        )
        if any(
            item.observed_at is not None and item.observed_at > self.completed_at
            for group in provenance_groups
            for item in group
        ):
            raise ValueError("lap evidence provenance cannot postdate lap completion")
        if len(set(self.hard_exclusions)) != len(self.hard_exclusions):
            raise ValueError("hard exclusions must be unique")
        if len(set(self.quality_warnings)) != len(self.quality_warnings):
            raise ValueError("quality warnings must be unique")
        return self


class PaceEstimationContext(FrozenDomainModel):
    """Race snapshot plus longer canonical evidence, all bounded to one cutoff."""

    race_state: RaceState
    as_of: datetime
    observations: tuple[ModellingLapObservation, ...] = ()
    data_quality: DataQuality = DataQuality()
    provenance: tuple[Provenance, ...] = ()

    @field_validator("as_of")
    @classmethod
    def cutoff_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value, "as_of")

    @model_validator(mode="after")
    def evidence_is_canonical_and_bounded(self):
        if self.as_of != self.race_state.observation_cutoff:
            raise ValueError("modelling cutoff must equal the canonical race-state cutoff")
        competitors = {car.competitor_id for car in self.race_state.competitors}
        keys = []
        for observation in self.observations:
            if observation.completed_at > self.as_of:
                raise ValueError("modelling evidence cannot postdate the cutoff")
            if observation.competitor_id not in competitors:
                raise ValueError("modelling evidence subject must exist in RaceState")
            keys.append((observation.competitor_id, observation.lap_number))
        if len(keys) != len(set(keys)):
            raise ValueError("modelling observations must be unique by competitor and lap")
        if tuple(keys) != tuple(sorted(keys, key=lambda item: (str(item[0]), item[1]))):
            raise ValueError("modelling observations require deterministic competitor/lap ordering")
        if any(item.observed_at is not None and item.observed_at > self.as_of for item in self.provenance):
            raise ValueError("context provenance cannot contain source observations after its cutoff")
        return self


class PaceModelConfig(FrozenDomainModel):
    model_name: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    minimum_clean_laps: int = Field(ge=2)
    lookback_laps: int = Field(default=8, ge=1)
    excluded_quality_warnings: tuple[LapQualityWarning, ...] = (LapQualityWarning.WEATHER_TRANSITION,)
    random_seed: int | None = None

    @field_validator("excluded_quality_warnings")
    @classmethod
    def warning_policy_is_unique_and_deterministic(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("excluded quality warnings must be unique")
        return tuple(reason for reason in LapQualityWarning if reason in value)

    @model_validator(mode="after")
    def sample_requirement_fits_lookback(self):
        if self.lookback_laps < self.minimum_clean_laps:
            raise ValueError("lookback_laps must be greater than or equal to minimum_clean_laps")
        return self

    def version(self) -> ModelVersion:
        payload = json.dumps(self.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        return ModelVersion(
            model_name=self.model_name,
            version=self.model_version,
            config_hash=f"sha256:{sha256(payload.encode('utf-8')).hexdigest()}",
        )


class FitDiagnostics(FrozenDomainModel):
    competitor_id: CompetitorId
    as_of: datetime
    candidate_laps: int = Field(ge=0)
    included_laps: int = Field(ge=0)
    excluded_laps: int = Field(ge=0)
    residual_median_s: float | None = None
    residual_median_absolute_s: float | None = Field(default=None, ge=0.0)
    warnings: tuple[str, ...] = ()
    model_version: ModelVersion
    data_quality: DataQuality = DataQuality()
    provenance: tuple[Provenance, ...] = ()

    @field_validator("as_of")
    @classmethod
    def cutoff_is_utc(cls, value: datetime) -> datetime:
        return _as_utc(value, "as_of")

    @model_validator(mode="after")
    def counts_reconcile(self):
        if self.included_laps + self.excluded_laps != self.candidate_laps:
            raise ValueError("included and excluded lap counts must equal candidate laps")
        _provenance_is_bounded(self.provenance, self.as_of, "fit diagnostics")
        return self


def _as_utc(value: datetime, name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be a usable timezone-aware timestamp")
    return value.astimezone(timezone.utc)
