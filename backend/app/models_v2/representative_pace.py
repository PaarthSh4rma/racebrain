"""Deterministic median baseline for recent representative clean-lap pace."""

from collections import Counter
from collections.abc import Sequence
from statistics import median

from app.domain_v2.enums import (
    ConfidenceLevel,
    DataQualityLevel,
    LapExclusionReason,
    LapQualityWarning,
    PaceAvailabilityReason,
)
from app.domain_v2.estimates import EvidenceWindow, PaceEstimate
from app.domain_v2.identity import CompetitorId
from app.domain_v2.modelling import FitDiagnostics, ModellingLapObservation, PaceEstimationContext, PaceModelConfig
from app.domain_v2.pace import (
    CompetitorPaceFit,
    FieldPaceResult,
    HardExclusionCount,
    PaceSelectionAudit,
    WarningExclusionCount,
)
from app.domain_v2.provenance import DataQuality, Provenance


BASELINE_PACE_CONFIG = PaceModelConfig(
    model_name="representative-clean-pace",
    model_version="0.1.0",
    lookback_laps=8,
    minimum_clean_laps=3,
    excluded_quality_warnings=(LapQualityWarning.WEATHER_TRANSITION,),
)

MODEL_LIMITATIONS = (
    "Does not separately identify or correct fuel burn.",
    "Does not separately identify or correct tyre-age degradation or compound performance.",
    "Does not separately identify or correct track evolution.",
    "Does not estimate traffic, dirty-air loss, or clean-air potential.",
    "Does not identify driver management or energy deployment effects.",
    "Does not model local weather effects beyond configured warning exclusions.",
    "The recent window may span different tyre states.",
)


def estimate_competitor_pace(
    context: PaceEstimationContext,
    competitor_id: CompetitorId,
    config: PaceModelConfig = BASELINE_PACE_CONFIG,
) -> CompetitorPaceFit:
    if competitor_id not in {car.competitor_id for car in context.race_state.competitors}:
        raise ValueError("pace subject must exist in canonical RaceState")
    candidates, included, audit = select_pace_evidence(context, competitor_id, config)
    model_version = config.version()
    insufficient = len(included) < config.minimum_clean_laps
    residual_median = None
    residual_median_absolute = None
    pace_value = None
    if not insufficient:
        pace_value = float(median(item.lap_time_s for item in included))
        residuals = tuple(item.lap_time_s - pace_value for item in included)
        residual_median = float(median(residuals))
        residual_median_absolute = float(median(abs(value) for value in residuals))
    evidence_quality = _pace_evidence_quality(included, config)
    diagnostic_warnings = list(evidence_quality.warnings)
    if insufficient:
        diagnostic_warnings.append(
            f"insufficient recent clean laps: {len(included)} available; {config.minimum_clean_laps} required"
        )
    model_provenance = _model_provenance(config)
    diagnostics = FitDiagnostics(
        competitor_id=competitor_id,
        as_of=context.as_of,
        candidate_laps=len(candidates),
        included_laps=len(included),
        excluded_laps=len(candidates) - len(included),
        residual_median_s=residual_median,
        residual_median_absolute_s=residual_median_absolute,
        warnings=tuple(diagnostic_warnings),
        model_version=model_version,
        data_quality=DataQuality(
            level=DataQualityLevel.INSUFFICIENT if insufficient else evidence_quality.level,
            completeness=None,
            warnings=tuple(diagnostic_warnings),
            missing_fields=evidence_quality.missing_fields,
        ),
        provenance=(model_provenance,),
    )
    if insufficient:
        return CompetitorPaceFit(
            competitor_id=competitor_id,
            diagnostics=diagnostics,
            selection_audit=audit,
            unavailable_reason=PaceAvailabilityReason.INSUFFICIENT_RECENT_CLEAN_LAPS,
        )
    evidence = EvidenceWindow(
        first_lap=min(item.lap_number for item in included),
        last_lap=max(item.lap_number for item in included),
        started_at=min(item.completed_at for item in included),
        ended_at=max(item.completed_at for item in included),
    )
    estimate = PaceEstimate(
        value=pace_value,
        competitor_id=competitor_id,
        as_of=context.as_of,
        sample_count=len(included),
        evidence_window=evidence,
        model_version=model_version,
        uncertainty=None,
        confidence=ConfidenceLevel.UNKNOWN,
        assumptions=(
            f"Median of clean admitted observations in trailing {config.lookback_laps}-lap-number window.",
            "Every factual hard exclusion is disqualifying.",
            "Configured quality-warning exclusions are disqualifying.",
        ),
        provenance=(model_provenance,),
        data_quality=evidence_quality,
        limitations=MODEL_LIMITATIONS,
    )
    return CompetitorPaceFit(
        competitor_id=competitor_id,
        estimate=estimate,
        diagnostics=diagnostics,
        selection_audit=audit,
    )


def select_pace_evidence(
    context: PaceEstimationContext,
    competitor_id: CompetitorId,
    config: PaceModelConfig = BASELINE_PACE_CONFIG,
) -> tuple[tuple[ModellingLapObservation, ...], tuple[ModellingLapObservation, ...], PaceSelectionAudit]:
    """Return the exact candidate and included evidence used by the point estimator."""

    if competitor_id not in {car.competitor_id for car in context.race_state.competitors}:
        raise ValueError("pace subject must exist in canonical RaceState")
    observations = tuple(item for item in context.observations if item.competitor_id == competitor_id)
    latest_lap = max((item.lap_number for item in observations), default=None)
    if latest_lap is None:
        candidates = ()
    else:
        first_candidate_lap = max(1, latest_lap - config.lookback_laps + 1)
        candidates = tuple(item for item in observations if first_candidate_lap <= item.lap_number <= latest_lap)
    configured_warnings = set(config.excluded_quality_warnings)
    included = []
    hard_counts = Counter()
    warning_counts = Counter()
    for item in candidates:
        hard = tuple(item.hard_exclusions)
        warnings = tuple(reason for reason in item.quality_warnings if reason in configured_warnings)
        if hard or warnings:
            hard_counts.update(hard)
            warning_counts.update(warnings)
        else:
            included.append(item)
    audit = PaceSelectionAudit(
        hard_exclusions=tuple(
            HardExclusionCount(reason=reason, lap_count=hard_counts[reason])
            for reason in _ordered_hard_reasons(hard_counts)
        ),
        warning_exclusions=tuple(
            WarningExclusionCount(warning=warning, lap_count=warning_counts[warning])
            for warning in _ordered_warning_reasons(warning_counts)
        ),
    )
    return candidates, tuple(included), audit


def estimate_field_pace(
    context: PaceEstimationContext,
    config: PaceModelConfig = BASELINE_PACE_CONFIG,
) -> FieldPaceResult:
    competitors = tuple(sorted((car.competitor_id for car in context.race_state.competitors), key=str))
    return FieldPaceResult(
        as_of=context.as_of,
        model_version=config.version(),
        competitors=tuple(estimate_competitor_pace(context, competitor, config) for competitor in competitors),
    )


def _pace_evidence_quality(
    observations: Sequence[ModellingLapObservation],
    config: PaceModelConfig,
) -> DataQuality:
    warnings = {
        warning
        for item in observations
        for warning in item.data_quality.warnings
        if "timing" in warning.lower() or "lap completion" in warning.lower() or "lap duration" in warning.lower()
    }
    relevant_missing = {"race_control_context"}
    if LapQualityWarning.WEATHER_TRANSITION in config.excluded_quality_warnings:
        relevant_missing.add("weather_context")
    missing_fields = tuple(
        field
        for field in ("race_control_context", "weather_context")
        if field in relevant_missing
        and any(field in item.data_quality.missing_fields for item in observations)
    )
    ordered_warnings = tuple(sorted(warnings))
    return DataQuality(
        level=DataQualityLevel.DEGRADED if ordered_warnings or missing_fields else DataQualityLevel.GOOD,
        completeness=None,
        warnings=ordered_warnings,
        missing_fields=missing_fields,
    )


def _model_provenance(config: PaceModelConfig) -> Provenance:
    version = config.version()
    return Provenance(
        source="RaceBrain representative clean-lap pace estimator",
        source_version=version.version,
        observed_at=None,
        transformations=(
            "selected configured trailing lap-number window from canonical PaceEstimationContext",
            "applied all factual hard exclusions and configured quality-warning exclusions",
            "aggregated included observed lap times with standard-library median",
        ),
        assumptions=(f"model={version.model_name}; config_hash={version.config_hash}",),
    )


def _ordered_hard_reasons(counts):
    return tuple(reason for reason in LapExclusionReason if counts[reason])


def _ordered_warning_reasons(counts):
    return tuple(reason for reason in LapQualityWarning if counts[reason])
