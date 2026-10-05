"""Explicit public API contracts for the V2 historical workbench."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.adapters.openf1_v2.modelling_history import ModellingHistoryDiagnostics
from app.application_v2.analyze_historical import HistoricalAnalysisResult
from app.domain_v2.enums import LapAdmissionRejectionReason
from app.domain_v2.identity import CompetitorId
from app.domain_v2.race_state import RaceState
from app.domain_v2.robustness import FieldPaceRobustnessResult, FieldTyreSlopeRobustnessResult


class HistoricalSessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    session_key: int
    meeting_key: int
    year: int
    event_name: str
    country_name: str
    location: str
    session_name: str
    session_type: str | None = None


class HistoricalDriverSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    driver_number: int
    full_name: str
    name_acronym: str | None = None
    team_name: str | None = None


class DecisionLapSummary(BaseModel):
    session_key: int
    driver_number: int
    laps: tuple[int, ...]


class HistoricalRaceStateApiRequest(BaseModel):
    model_config = ConfigDict(strict=True)
    session_key: int = Field(gt=0)
    driver_number: int = Field(gt=0)
    decision_lap: int = Field(gt=0)


class ReconstructionDiagnosticsResponse(BaseModel):
    malformed_records: int
    future_records: int
    untimed_records: int
    duplicate_records: int
    excluded_competitors: int
    foreign_session_records: int
    bounded_pit_lane_passages: int
    included_records: dict[str, int]
    cache_hits: dict[str, bool]


class HistoricalRaceStateResponse(BaseModel):
    race_state: RaceState
    diagnostics: ReconstructionDiagnosticsResponse


class ModellingDiagnosticsResponse(BaseModel):
    source_lap_rows: int
    admitted_observations: int
    admission_rejections: dict[LapAdmissionRejectionReason, int]
    rows_bounded_out: int
    foreign_session_rows: int
    unmapped_competitor_rows: int
    exact_duplicate_laps: int
    conflicting_laps: int
    future_stint_starts: int
    ambiguous_stint_annotations: int
    tyre_annotations: int
    weather_alignments: int
    race_control_alignments: int
    gap_alignments: int
    pit_lane_affected_observations: int
    feed_cache_hits: dict[str, bool]

    @classmethod
    def from_domain(
        cls,
        diagnostics: ModellingHistoryDiagnostics,
        feed_cache_hits: dict[str, bool],
    ) -> "ModellingDiagnosticsResponse":
        return cls(**diagnostics.__dict__, feed_cache_hits=feed_cache_hits)


class ExcludedLapEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    lap_number: int = Field(ge=1)
    reasons: tuple[str, ...] = Field(min_length=1)


class ModelLapEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    candidate_laps: tuple[int, ...]
    included_laps: tuple[int, ...]
    excluded_laps: tuple[ExcludedLapEvidenceResponse, ...]


class CompetitorAnalysisEvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    competitor_id: CompetitorId
    pace: ModelLapEvidenceResponse
    tyre_age_slope: ModelLapEvidenceResponse


class HistoricalAnalysisResponse(BaseModel):
    race_state: RaceState
    reconstruction_diagnostics: ReconstructionDiagnosticsResponse
    modelling_diagnostics: ModellingDiagnosticsResponse
    pace: FieldPaceRobustnessResult
    tyre_age_slope: FieldTyreSlopeRobustnessResult
    evidence: tuple[CompetitorAnalysisEvidenceResponse, ...]

    @classmethod
    def from_result(cls, result: HistoricalAnalysisResult) -> "HistoricalAnalysisResponse":
        return cls(
            race_state=result.race_state,
            reconstruction_diagnostics=ReconstructionDiagnosticsResponse(
                **result.reconstruction_diagnostics.__dict__
            ),
            modelling_diagnostics=ModellingDiagnosticsResponse.from_domain(
                result.modelling_diagnostics,
                result.modelling_feed_cache_hits,
            ),
            pace=result.pace,
            tyre_age_slope=result.tyre_age_slope,
            evidence=tuple(
                CompetitorAnalysisEvidenceResponse.model_validate(item.__dict__)
                for item in result.evidence
            ),
        )

    @model_validator(mode="after")
    def aggregate_reconciles(self):
        cutoff = self.race_state.observation_cutoff
        if self.pace.as_of != cutoff or self.tyre_age_slope.as_of != cutoff:
            raise ValueError("analysis model cutoffs must equal the canonical RaceState cutoff")
        canonical = tuple(sorted((car.competitor_id for car in self.race_state.competitors), key=str))
        pace_ids = tuple(item.competitor_id for item in self.pace.competitors)
        tyre_ids = tuple(item.competitor_id for item in self.tyre_age_slope.competitors)
        if pace_ids != canonical or tyre_ids != canonical:
            raise ValueError("analysis model subjects must match canonical RaceState competitors")
        evidence_ids = tuple(item.competitor_id for item in self.evidence)
        if evidence_ids != canonical:
            raise ValueError("analysis evidence subjects must match canonical RaceState competitors")
        return self
