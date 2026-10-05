"""Cohesive application service for a historical V2 model analysis."""

from dataclasses import dataclass

from app.adapters.openf1_v2.mapper import ReconstructionDiagnostics
from app.adapters.openf1_v2.modelling_history import ModellingHistoryDiagnostics
from app.application_v2.build_pace_context import build_historical_pace_context
from app.application_v2.reconstruct_race_state import HistoricalRaceStateRequest
from app.data_sources.openf1_client import OpenF1Client
from app.domain_v2.race_state import RaceState
from app.domain_v2.robustness import FieldPaceRobustnessResult, FieldTyreSlopeRobustnessResult
from app.domain_v2.identity import CompetitorId
from app.domain_v2.modelling import ModellingLapObservation, PaceEstimationContext
from app.models_v2.model_robustness import (
    analyze_field_pace_robustness,
    analyze_field_tyre_slope_robustness,
)
from app.models_v2.representative_pace import BASELINE_PACE_CONFIG, select_pace_evidence
from app.models_v2.tyre_age_slope import BASELINE_TYRE_SLOPE_CONFIG, _select_clean_laps


@dataclass(frozen=True)
class ExcludedLapEvidence:
    lap_number: int
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ModelLapEvidence:
    candidate_laps: tuple[int, ...]
    included_laps: tuple[int, ...]
    excluded_laps: tuple[ExcludedLapEvidence, ...]


@dataclass(frozen=True)
class CompetitorAnalysisEvidence:
    competitor_id: CompetitorId
    pace: ModelLapEvidence
    tyre_age_slope: ModelLapEvidence


@dataclass(frozen=True)
class HistoricalAnalysisResult:
    race_state: RaceState
    reconstruction_diagnostics: ReconstructionDiagnostics
    modelling_diagnostics: ModellingHistoryDiagnostics
    modelling_feed_cache_hits: dict[str, bool]
    pace: FieldPaceRobustnessResult
    tyre_age_slope: FieldTyreSlopeRobustnessResult
    evidence: tuple[CompetitorAnalysisEvidence, ...]


def analyze_historical_decision_point(
    request: HistoricalRaceStateRequest,
    client: OpenF1Client | None = None,
) -> HistoricalAnalysisResult:
    """Build one bounded context and evaluate every accepted V2.2 model from it."""

    built = build_historical_pace_context(request, client)
    context = built.context
    pace = analyze_field_pace_robustness(context)
    tyre_age_slope = analyze_field_tyre_slope_robustness(context)
    return HistoricalAnalysisResult(
        race_state=context.race_state,
        reconstruction_diagnostics=built.reconstruction_diagnostics,
        modelling_diagnostics=built.diagnostics,
        modelling_feed_cache_hits=built.modelling_feed_cache_hits,
        pace=pace,
        tyre_age_slope=tyre_age_slope,
        evidence=_field_evidence(context, pace, tyre_age_slope),
    )


def _field_evidence(
    context: PaceEstimationContext,
    pace: FieldPaceRobustnessResult,
    tyre: FieldTyreSlopeRobustnessResult,
) -> tuple[CompetitorAnalysisEvidence, ...]:
    tyre_by_id = {item.competitor_id: item for item in tyre.competitors}
    evidence = []
    for pace_result in pace.competitors:
        competitor_id = pace_result.competitor_id
        pace_candidates, pace_included, _ = select_pace_evidence(context, competitor_id, BASELINE_PACE_CONFIG)
        tyre_result = tyre_by_id[competitor_id]
        tyre_diagnostics = tyre_result.point_fit.diagnostics
        competitor_observations = tuple(
            item for item in context.observations if item.competitor_id == competitor_id
        )
        selected_stint = tyre_diagnostics.stint_number
        if selected_stint is None and tyre_diagnostics.candidate_laps and competitor_observations:
            selected_stint = max(competitor_observations, key=lambda item: item.lap_number).stint_number
        tyre_candidates = tuple(
            item for item in competitor_observations
            if selected_stint is not None and item.stint_number == selected_stint
        )
        tyre_included, _ = _select_clean_laps(tyre_candidates, BASELINE_TYRE_SLOPE_CONFIG)
        if len(pace_candidates) != pace_result.point_fit.diagnostics.candidate_laps:
            raise ValueError("pace analysis evidence must match point-fit candidates")
        if len(pace_included) != pace_result.point_fit.diagnostics.included_laps:
            raise ValueError("pace analysis evidence must match point-fit included laps")
        if len(tyre_candidates) != tyre_diagnostics.candidate_laps:
            raise ValueError("tyre analysis evidence must match point-fit candidates")
        if len(tyre_included) != tyre_diagnostics.included_laps:
            raise ValueError("tyre analysis evidence must match point-fit included laps")
        evidence.append(CompetitorAnalysisEvidence(
            competitor_id=competitor_id,
            pace=_lap_evidence(pace_candidates, tuple(pace_included), BASELINE_PACE_CONFIG.excluded_quality_warnings),
            tyre_age_slope=_lap_evidence(tyre_candidates, tuple(tyre_included), BASELINE_TYRE_SLOPE_CONFIG.excluded_quality_warnings),
        ))
    return tuple(evidence)


def _lap_evidence(
    candidates: tuple[ModellingLapObservation, ...],
    included: tuple[ModellingLapObservation, ...],
    excluded_warnings,
) -> ModelLapEvidence:
    included_laps = {item.lap_number for item in included}
    configured_warnings = set(excluded_warnings)
    excluded = tuple(
        ExcludedLapEvidence(
            lap_number=item.lap_number,
            reasons=tuple(reason.value for reason in item.hard_exclusions)
            + tuple(warning.value for warning in item.quality_warnings if warning in configured_warnings),
        )
        for item in candidates
        if item.lap_number not in included_laps
    )
    return ModelLapEvidence(
        candidate_laps=tuple(item.lap_number for item in candidates),
        included_laps=tuple(item.lap_number for item in included),
        excluded_laps=excluded,
    )
