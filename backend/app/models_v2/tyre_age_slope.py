"""Deterministic OLS baseline for descriptive within-stint tyre-age pace slope."""

from collections import Counter
from statistics import mean, median

from app.domain_v2.enums import (
    ConfidenceLevel,
    DataQualityLevel,
    LapExclusionReason,
    LapQualityWarning,
    TyreCompound,
    TyreSlopeAvailabilityReason,
)
from app.domain_v2.estimates import EvidenceWindow, TyreDegradationEstimate
from app.domain_v2.identity import CompetitorId
from app.domain_v2.modelling import ModellingLapObservation, PaceEstimationContext, TyreSlopeModelConfig
from app.domain_v2.pace import HardExclusionCount, PaceSelectionAudit, WarningExclusionCount
from app.domain_v2.provenance import DataQuality, Provenance
from app.domain_v2.tyre_slope import CompetitorTyreSlopeFit, FieldTyreSlopeResult, TyreSlopeDiagnostics


BASELINE_TYRE_SLOPE_CONFIG = TyreSlopeModelConfig(
    model_name="empirical-tyre-age-slope",
    model_version="0.1.0",
    minimum_clean_laps=5,
    minimum_tyre_age_span_laps=4,
    excluded_quality_warnings=(LapQualityWarning.WEATHER_TRANSITION,),
)

MODEL_LIMITATIONS = (
    "Describes association within one bounded stint; it is not pure physical tyre degradation.",
    "Does not separately identify or correct fuel burn.",
    "Does not separately identify or correct track evolution.",
    "Does not estimate traffic, dirty-air loss, or clean-air potential.",
    "Does not identify driver management or energy deployment effects.",
    "Does not model local weather effects beyond configured warning exclusions.",
    "Tyre age is canonical reconstructed evidence, not physical tyre-set identity.",
)


def estimate_competitor_tyre_slope(
    context: PaceEstimationContext,
    competitor_id: CompetitorId,
    config: TyreSlopeModelConfig = BASELINE_TYRE_SLOPE_CONFIG,
) -> CompetitorTyreSlopeFit:
    if competitor_id not in {car.competitor_id for car in context.race_state.competitors}:
        raise ValueError("tyre-slope subject must exist in canonical RaceState")
    observations = tuple(item for item in context.observations if item.competitor_id == competitor_id)
    if not observations:
        return _structurally_unavailable(
            competitor_id, context, config, (), TyreSlopeAvailabilityReason.NO_OBSERVATIONS,
            "no admitted modelling observations exist for the competitor",
        )
    latest = max(observations, key=lambda item: item.lap_number)
    if latest.compound is None or latest.tyre_age_laps is None or latest.stint_number is None:
        return _structurally_unavailable(
            competitor_id, context, config, (), TyreSlopeAvailabilityReason.MISSING_TYRE_ANNOTATION,
            "latest admitted lap lacks a complete canonical compound, tyre age, and bounded stint annotation",
        )
    candidates = tuple(item for item in observations if item.stint_number == latest.stint_number)
    if any(item.compound is None or item.tyre_age_laps is None for item in candidates):
        return _structurally_unavailable(
            competitor_id, context, config, candidates, TyreSlopeAvailabilityReason.MISSING_TYRE_ANNOTATION,
            "selected bounded stint contains incomplete canonical tyre annotation",
            compound=latest.compound, stint_number=latest.stint_number,
        )
    compounds = {item.compound for item in candidates}
    if TyreCompound.UNKNOWN in compounds:
        return _structurally_unavailable(
            competitor_id, context, config, candidates, TyreSlopeAvailabilityReason.UNKNOWN_COMPOUND,
            "selected bounded stint does not have an identified tyre compound",
            compound=TyreCompound.UNKNOWN, stint_number=latest.stint_number,
        )
    if len(compounds) != 1:
        return _structurally_unavailable(
            competitor_id, context, config, candidates, TyreSlopeAvailabilityReason.MIXED_COMPOUND,
            "selected bounded stint contains mixed compound annotations",
            stint_number=latest.stint_number,
        )
    compound = next(iter(compounds))
    if not _tyre_age_progression_is_consistent(candidates):
        return _structurally_unavailable(
            competitor_id, context, config, candidates,
            TyreSlopeAvailabilityReason.INCONSISTENT_TYRE_AGE_PROGRESSION,
            "selected bounded stint does not preserve lap-for-lap tyre-age progression",
            compound=compound, stint_number=latest.stint_number,
        )

    included, audit = _select_clean_laps(candidates, config)
    quality = _tyre_evidence_quality(included, config)
    ages = tuple(item.tyre_age_laps for item in included)
    minimum_age = min(ages) if ages else None
    maximum_age = max(ages) if ages else None
    age_span = maximum_age - minimum_age if ages else None
    unavailable_reason = None
    warning = None
    if len(included) < config.minimum_clean_laps:
        unavailable_reason = TyreSlopeAvailabilityReason.INSUFFICIENT_CLEAN_LAPS
        warning = f"insufficient clean laps: {len(included)} available; {config.minimum_clean_laps} required"
    elif age_span < config.minimum_tyre_age_span_laps:
        unavailable_reason = TyreSlopeAvailabilityReason.INSUFFICIENT_TYRE_AGE_SPAN
        warning = (
            f"insufficient tyre-age span: {age_span} laps available; "
            f"{config.minimum_tyre_age_span_laps} required"
        )

    model_version = config.version()
    model_provenance = _model_provenance(config)
    if unavailable_reason is not None:
        warnings = quality.warnings + (warning,)
        diagnostics = TyreSlopeDiagnostics(
            competitor_id=competitor_id,
            as_of=context.as_of,
            candidate_laps=len(candidates),
            included_laps=len(included),
            excluded_laps=len(candidates) - len(included),
            warnings=warnings,
            model_version=model_version,
            data_quality=DataQuality(
                level=DataQualityLevel.INSUFFICIENT,
                completeness=None,
                warnings=warnings,
                missing_fields=quality.missing_fields,
            ),
            provenance=(model_provenance,),
            compound=compound,
            stint_number=latest.stint_number,
            minimum_tyre_age_laps=minimum_age,
            maximum_tyre_age_laps=maximum_age,
            tyre_age_span_laps=age_span,
        )
        return CompetitorTyreSlopeFit(
            competitor_id=competitor_id,
            diagnostics=diagnostics,
            selection_audit=audit,
            unavailable_reason=unavailable_reason,
        )

    slope, intercept = _ordinary_least_squares(included)
    residuals = tuple(item.lap_time_s - (intercept + slope * item.tyre_age_laps) for item in included)
    diagnostics = TyreSlopeDiagnostics(
        competitor_id=competitor_id,
        as_of=context.as_of,
        candidate_laps=len(candidates),
        included_laps=len(included),
        excluded_laps=len(candidates) - len(included),
        residual_median_s=float(median(residuals)),
        residual_median_absolute_s=float(median(abs(value) for value in residuals)),
        warnings=quality.warnings,
        model_version=model_version,
        data_quality=quality,
        provenance=(model_provenance,),
        compound=compound,
        stint_number=latest.stint_number,
        minimum_tyre_age_laps=minimum_age,
        maximum_tyre_age_laps=maximum_age,
        tyre_age_span_laps=age_span,
        intercept_s=intercept,
    )
    evidence = EvidenceWindow(
        first_lap=min(item.lap_number for item in included),
        last_lap=max(item.lap_number for item in included),
        started_at=min(item.completed_at for item in included),
        ended_at=max(item.completed_at for item in included),
    )
    estimate = TyreDegradationEstimate(
        value=slope,
        competitor_id=competitor_id,
        as_of=context.as_of,
        compound=compound,
        stint_number=latest.stint_number,
        minimum_tyre_age_laps=minimum_age,
        maximum_tyre_age_laps=maximum_age,
        sample_count=len(included),
        evidence_window=evidence,
        model_version=model_version,
        uncertainty=None,
        confidence=ConfidenceLevel.UNKNOWN,
        assumptions=(
            "Closed-form ordinary least squares over one latest canonical bounded stint.",
            "Every factual hard exclusion is disqualifying.",
            "Configured quality-warning exclusions are disqualifying.",
        ),
        provenance=(model_provenance,),
        data_quality=quality,
        limitations=MODEL_LIMITATIONS,
    )
    return CompetitorTyreSlopeFit(
        competitor_id=competitor_id,
        estimate=estimate,
        diagnostics=diagnostics,
        selection_audit=audit,
    )


def estimate_field_tyre_slopes(
    context: PaceEstimationContext,
    config: TyreSlopeModelConfig = BASELINE_TYRE_SLOPE_CONFIG,
) -> FieldTyreSlopeResult:
    competitors = tuple(sorted((car.competitor_id for car in context.race_state.competitors), key=str))
    return FieldTyreSlopeResult(
        as_of=context.as_of,
        model_version=config.version(),
        competitors=tuple(estimate_competitor_tyre_slope(context, competitor, config) for competitor in competitors),
    )


def _select_clean_laps(candidates, config):
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
    return included, PaceSelectionAudit(
        hard_exclusions=tuple(
            HardExclusionCount(reason=reason, lap_count=hard_counts[reason])
            for reason in LapExclusionReason if hard_counts[reason]
        ),
        warning_exclusions=tuple(
            WarningExclusionCount(warning=reason, lap_count=warning_counts[reason])
            for reason in LapQualityWarning if warning_counts[reason]
        ),
    )


def _tyre_age_progression_is_consistent(candidates) -> bool:
    ordered = sorted(candidates, key=lambda item: item.lap_number)
    return all(
        current.tyre_age_laps - previous.tyre_age_laps == current.lap_number - previous.lap_number
        for previous, current in zip(ordered, ordered[1:])
    )


def _ordinary_least_squares(observations):
    x_mean = mean(item.tyre_age_laps for item in observations)
    y_mean = mean(item.lap_time_s for item in observations)
    denominator = sum((item.tyre_age_laps - x_mean) ** 2 for item in observations)
    slope = sum(
        (item.tyre_age_laps - x_mean) * (item.lap_time_s - y_mean)
        for item in observations
    ) / denominator
    return float(slope), float(y_mean - slope * x_mean)


def _tyre_evidence_quality(observations, config):
    warnings = {
        warning
        for item in observations
        for warning in item.data_quality.warnings
        if "timing" in warning.lower() or "lap completion" in warning.lower() or "lap duration" in warning.lower()
    }
    relevant_missing = {"tyre_annotation", "race_control_context"}
    if LapQualityWarning.WEATHER_TRANSITION in config.excluded_quality_warnings:
        relevant_missing.add("weather_context")
    missing_fields = tuple(
        field for field in ("tyre_annotation", "race_control_context", "weather_context")
        if field in relevant_missing and any(field in item.data_quality.missing_fields for item in observations)
    )
    ordered_warnings = tuple(sorted(warnings))
    return DataQuality(
        level=DataQualityLevel.DEGRADED if ordered_warnings or missing_fields else DataQualityLevel.GOOD,
        completeness=None,
        warnings=ordered_warnings,
        missing_fields=missing_fields,
    )


def _structurally_unavailable(
    competitor_id, context, config, candidates, reason, warning, *, compound=None, stint_number=None,
):
    provenance = _model_provenance(config)
    diagnostics = TyreSlopeDiagnostics(
        competitor_id=competitor_id,
        as_of=context.as_of,
        candidate_laps=len(candidates),
        included_laps=0,
        excluded_laps=len(candidates),
        warnings=(warning,),
        model_version=config.version(),
        data_quality=DataQuality(
            level=DataQualityLevel.INSUFFICIENT,
            completeness=None,
            warnings=(warning,),
            missing_fields=("tyre_annotation",) if reason is TyreSlopeAvailabilityReason.MISSING_TYRE_ANNOTATION else (),
        ),
        provenance=(provenance,),
        compound=compound,
        stint_number=stint_number,
    )
    return CompetitorTyreSlopeFit(
        competitor_id=competitor_id,
        diagnostics=diagnostics,
        unavailable_reason=reason,
    )


def _model_provenance(config):
    version = config.version()
    return Provenance(
        source="RaceBrain empirical tyre-age pace slope estimator",
        source_version=version.version,
        observed_at=None,
        transformations=(
            "selected the latest canonical bounded stint and identified compound",
            "applied all factual hard exclusions and configured quality-warning exclusions",
            "fit closed-form ordinary least squares of lap time against canonical tyre age",
        ),
        assumptions=(f"model={version.model_name}; config_hash={version.config_hash}",),
    )
