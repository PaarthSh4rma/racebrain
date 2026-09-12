"""Deterministic empirical robustness analysis for accepted V2.2 point models."""

from collections import Counter
from math import ceil, floor

from app.domain_v2.enums import (
    PaceQuantileMethod,
    RobustnessAvailabilityReason,
    SlopeSign,
)
from app.domain_v2.estimates import EmpiricalQuantiles, StatisticalInterval
from app.domain_v2.identity import CompetitorId
from app.domain_v2.modelling import (
    ModelRobustnessConfig,
    ModellingLapObservation,
    PaceEstimationContext,
    PaceModelConfig,
    TyreSlopeModelConfig,
)
from app.domain_v2.provenance import Provenance
from app.domain_v2.robustness import (
    FieldPaceRobustnessResult,
    FieldTyreSlopeRobustnessResult,
    LeaveOneOutSlope,
    PaceRobustnessDiagnostics,
    PaceRobustnessResult,
    SlopeSignCounts,
    TYRE_SLOPE_SENSITIVITY_METHOD,
    TyreSlopeRobustnessDiagnostics,
    TyreSlopeRobustnessResult,
)
from app.models_v2.representative_pace import (
    BASELINE_PACE_CONFIG,
    estimate_competitor_pace,
    select_pace_evidence,
)
from app.models_v2.tyre_age_slope import (
    BASELINE_TYRE_SLOPE_CONFIG,
    _ordinary_least_squares,
    _select_clean_laps,
    estimate_competitor_tyre_slope,
)


BASELINE_ROBUSTNESS_CONFIG = ModelRobustnessConfig(
    model_name="empirical-model-robustness",
    model_version="0.1.0",
    pace_quantiles=(0.1, 0.5, 0.9),
    pace_quantile_method=PaceQuantileMethod.LINEAR_INTERPOLATION,
    tyre_slope_zero_tolerance=1e-9,
)

PACE_ROBUSTNESS_LIMITATIONS = (
    "Quantiles describe only the empirical distribution of accepted clean lap times.",
    "The p10-p90 spread is not a confidence, prediction, forecast, or probability interval.",
    "The analysis does not resolve fuel, tyre, traffic, weather, track-evolution, or driver-management confounding.",
)

TYRE_ROBUSTNESS_LIMITATIONS = (
    "Leave-one-observation-out refits are deterministic sensitivity perturbations, not cross-validation accuracy.",
    "The sensitivity envelope is not a confidence, prediction, probability, or posterior interval.",
    "Sign stability describes only whether every diagnostic refit retains the nominal tolerance-classified sign.",
    "The analysis does not resolve fuel, track-evolution, traffic, weather, or driver-management confounding.",
)

SENSITIVITY_ENVELOPE_METHOD = TYRE_SLOPE_SENSITIVITY_METHOD


def analyze_competitor_pace_robustness(
    context: PaceEstimationContext,
    competitor_id: CompetitorId,
    point_config: PaceModelConfig = BASELINE_PACE_CONFIG,
    robustness_config: ModelRobustnessConfig = BASELINE_ROBUSTNESS_CONFIG,
) -> PaceRobustnessResult:
    point_fit = estimate_competitor_pace(context, competitor_id, point_config)
    robustness_version = robustness_config.version()
    provenance = (_pace_provenance(point_config, robustness_config),)
    point_quality = point_fit.estimate.data_quality if point_fit.estimate else point_fit.diagnostics.data_quality
    if point_fit.estimate is None:
        return PaceRobustnessResult(
            competitor_id=competitor_id,
            as_of=context.as_of,
            point_model_version=point_config.version(),
            robustness_model_version=robustness_version,
            point_fit=point_fit,
            unavailable_reason=RobustnessAvailabilityReason.POINT_ESTIMATE_UNAVAILABLE,
            data_quality=point_quality,
            provenance=provenance,
            limitations=PACE_ROBUSTNESS_LIMITATIONS,
        )

    candidates, included, audit = select_pace_evidence(context, competitor_id, point_config)
    if (
        len(candidates) != point_fit.diagnostics.candidate_laps
        or len(included) != point_fit.estimate.sample_count
        or audit != point_fit.selection_audit
    ):
        raise ValueError("pace robustness evidence must reconcile with the accepted point fit")
    values = tuple(sorted(item.lap_time_s for item in included))
    p10, p50, p90 = (
        _linear_interpolated_quantile(values, quantile)
        for quantile in robustness_config.pace_quantiles
    )
    if p50 != point_fit.estimate.value:
        raise ValueError("pace robustness p50 must equal the accepted median point estimate")
    diagnostics = PaceRobustnessDiagnostics(
        quantile_method=robustness_config.pace_quantile_method,
        quantiles=EmpiricalQuantiles(p10=p10, p50=p50, p90=p90, sample_count=len(values)),
        minimum_lap_time_s=values[0],
        maximum_lap_time_s=values[-1],
        p90_p10_spread_s=p90 - p10,
    )
    return PaceRobustnessResult(
        competitor_id=competitor_id,
        as_of=context.as_of,
        point_model_version=point_config.version(),
        robustness_model_version=robustness_version,
        point_fit=point_fit,
        diagnostics=diagnostics,
        data_quality=point_quality,
        provenance=provenance,
        limitations=PACE_ROBUSTNESS_LIMITATIONS,
    )


def analyze_field_pace_robustness(
    context: PaceEstimationContext,
    point_config: PaceModelConfig = BASELINE_PACE_CONFIG,
    robustness_config: ModelRobustnessConfig = BASELINE_ROBUSTNESS_CONFIG,
) -> FieldPaceRobustnessResult:
    competitors = tuple(sorted((car.competitor_id for car in context.race_state.competitors), key=str))
    return FieldPaceRobustnessResult(
        as_of=context.as_of,
        point_model_version=point_config.version(),
        robustness_model_version=robustness_config.version(),
        competitors=tuple(
            analyze_competitor_pace_robustness(context, competitor, point_config, robustness_config)
            for competitor in competitors
        ),
    )


def analyze_competitor_tyre_slope_robustness(
    context: PaceEstimationContext,
    competitor_id: CompetitorId,
    point_config: TyreSlopeModelConfig = BASELINE_TYRE_SLOPE_CONFIG,
    robustness_config: ModelRobustnessConfig = BASELINE_ROBUSTNESS_CONFIG,
) -> TyreSlopeRobustnessResult:
    point_fit = estimate_competitor_tyre_slope(context, competitor_id, point_config)
    robustness_version = robustness_config.version()
    provenance = (_tyre_provenance(point_config, robustness_config),)
    point_quality = point_fit.estimate.data_quality if point_fit.estimate else point_fit.diagnostics.data_quality
    if point_fit.estimate is None:
        return TyreSlopeRobustnessResult(
            competitor_id=competitor_id,
            as_of=context.as_of,
            point_model_version=point_config.version(),
            robustness_model_version=robustness_version,
            point_fit=point_fit,
            unavailable_reason=RobustnessAvailabilityReason.POINT_ESTIMATE_UNAVAILABLE,
            data_quality=point_quality,
            provenance=provenance,
            limitations=TYRE_ROBUSTNESS_LIMITATIONS,
        )

    included = _accepted_tyre_evidence(context, point_fit, point_config)
    refits = []
    for omitted in included:
        remaining = tuple(item for item in included if item.lap_number != omitted.lap_number)
        if not _ols_is_identifiable(remaining):
            return TyreSlopeRobustnessResult(
                competitor_id=competitor_id,
                as_of=context.as_of,
                point_model_version=point_config.version(),
                robustness_model_version=robustness_version,
                point_fit=point_fit,
                unavailable_reason=RobustnessAvailabilityReason.INVALID_DIAGNOSTIC_REFIT,
                data_quality=point_quality,
                provenance=provenance,
                limitations=TYRE_ROBUSTNESS_LIMITATIONS
                + (f"Omitting lap {omitted.lap_number} leaves a mathematically invalid OLS refit.",),
            )
        slope, _ = _ordinary_least_squares(remaining)
        refits.append(
            LeaveOneOutSlope(
                omitted_lap_number=omitted.lap_number,
                slope_s_per_lap_per_lap=slope,
                sign=classify_slope_sign(slope, robustness_config.tyre_slope_zero_tolerance),
            )
        )

    nominal = point_fit.estimate.value
    nominal_sign = classify_slope_sign(nominal, robustness_config.tyre_slope_zero_tolerance)
    slopes = tuple(item.slope_s_per_lap_per_lap for item in refits)
    deviations = tuple(abs(value - nominal) for value in slopes)
    maximum_deviation = max(deviations)
    influential_lap = min(
        item.omitted_lap_number
        for item, deviation in zip(refits, deviations)
        if deviation == maximum_deviation
    )
    signs = Counter(item.sign for item in refits)
    diagnostics = TyreSlopeRobustnessDiagnostics(
        nominal_slope_s_per_lap_per_lap=nominal,
        nominal_sign=nominal_sign,
        zero_tolerance_s_per_lap_per_lap=robustness_config.tyre_slope_zero_tolerance,
        leave_one_out_refits=tuple(refits),
        leave_one_out_refit_count=len(refits),
        leave_one_out_min_s_per_lap_per_lap=min(slopes),
        leave_one_out_max_s_per_lap_per_lap=max(slopes),
        sensitivity_envelope=StatisticalInterval(
            lower=min(nominal, *slopes),
            upper=max(nominal, *slopes),
            coverage=None,
            method=SENSITIVITY_ENVELOPE_METHOD,
        ),
        sign_stable=all(item.sign is nominal_sign for item in refits),
        sign_counts=SlopeSignCounts(
            negative=signs[SlopeSign.NEGATIVE],
            zero=signs[SlopeSign.ZERO],
            positive=signs[SlopeSign.POSITIVE],
        ),
        maximum_absolute_deviation_s_per_lap_per_lap=maximum_deviation,
        most_influential_omitted_lap=influential_lap,
    )
    return TyreSlopeRobustnessResult(
        competitor_id=competitor_id,
        as_of=context.as_of,
        point_model_version=point_config.version(),
        robustness_model_version=robustness_version,
        point_fit=point_fit,
        diagnostics=diagnostics,
        data_quality=point_quality,
        provenance=provenance,
        limitations=TYRE_ROBUSTNESS_LIMITATIONS,
    )


def analyze_field_tyre_slope_robustness(
    context: PaceEstimationContext,
    point_config: TyreSlopeModelConfig = BASELINE_TYRE_SLOPE_CONFIG,
    robustness_config: ModelRobustnessConfig = BASELINE_ROBUSTNESS_CONFIG,
) -> FieldTyreSlopeRobustnessResult:
    competitors = tuple(sorted((car.competitor_id for car in context.race_state.competitors), key=str))
    return FieldTyreSlopeRobustnessResult(
        as_of=context.as_of,
        point_model_version=point_config.version(),
        robustness_model_version=robustness_config.version(),
        competitors=tuple(
            analyze_competitor_tyre_slope_robustness(context, competitor, point_config, robustness_config)
            for competitor in competitors
        ),
    )


def classify_slope_sign(slope: float, zero_tolerance: float) -> SlopeSign:
    if zero_tolerance < 0:
        raise ValueError("slope zero tolerance cannot be negative")
    if slope > zero_tolerance:
        return SlopeSign.POSITIVE
    if slope < -zero_tolerance:
        return SlopeSign.NEGATIVE
    return SlopeSign.ZERO


def _linear_interpolated_quantile(sorted_values: tuple[float, ...], quantile: float) -> float:
    if not sorted_values:
        raise ValueError("empirical quantiles require at least one value")
    if not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must be between zero and one")
    position = (len(sorted_values) - 1) * quantile
    lower_index = floor(position)
    upper_index = ceil(position)
    if lower_index == upper_index:
        return float(sorted_values[lower_index])
    weight = position - lower_index
    return float(sorted_values[lower_index] + (sorted_values[upper_index] - sorted_values[lower_index]) * weight)


def _accepted_tyre_evidence(context, point_fit, point_config) -> tuple[ModellingLapObservation, ...]:
    candidates = tuple(
        item
        for item in context.observations
        if item.competitor_id == point_fit.competitor_id
        and item.stint_number == point_fit.estimate.stint_number
    )
    included, audit = _select_clean_laps(candidates, point_config)
    included = tuple(included)
    estimate = point_fit.estimate
    if (
        len(candidates) != point_fit.diagnostics.candidate_laps
        or len(included) != estimate.sample_count
        or audit != point_fit.selection_audit
        or min(item.tyre_age_laps for item in included) != estimate.minimum_tyre_age_laps
        or max(item.tyre_age_laps for item in included) != estimate.maximum_tyre_age_laps
    ):
        raise ValueError("tyre robustness evidence must reconcile with the accepted point fit")
    nominal, _ = _ordinary_least_squares(included)
    if nominal != estimate.value:
        raise ValueError("tyre robustness evidence must reproduce the accepted nominal slope")
    return included


def _ols_is_identifiable(observations: tuple[ModellingLapObservation, ...]) -> bool:
    if len(observations) < 2:
        return False
    ages = tuple(item.tyre_age_laps for item in observations)
    mean_age = sum(ages) / len(ages)
    denominator = sum((age - mean_age) ** 2 for age in ages)
    return len(set(ages)) >= 2 and denominator > 0


def _pace_provenance(point_config, robustness_config) -> Provenance:
    point_version = point_config.version()
    version = robustness_config.version()
    return Provenance(
        source="RaceBrain empirical pace robustness analysis",
        source_version=version.version,
        observed_at=None,
        transformations=(
            "reused exact accepted representative-pace clean-lap evidence",
            "calculated empirical p10, p50, and p90 with deterministic linear interpolation",
        ),
        assumptions=(
            f"point_model={point_version.model_name}; point_config_hash={point_version.config_hash}",
            f"robustness_model={version.model_name}; robustness_config_hash={version.config_hash}",
            "quantiles describe selected observed lap times and are non-probabilistic",
        ),
    )


def _tyre_provenance(point_config, robustness_config) -> Provenance:
    point_version = point_config.version()
    version = robustness_config.version()
    return Provenance(
        source="RaceBrain empirical tyre-slope robustness analysis",
        source_version=version.version,
        observed_at=None,
        transformations=(
            "reused exact accepted tyre-slope clean-lap evidence",
            "omitted one observation per diagnostic refit using the accepted closed-form OLS formula",
            "classified slope signs with the configured explicit zero tolerance",
            "formed a deterministic non-probabilistic sensitivity envelope",
        ),
        assumptions=(
            f"point_model={point_version.model_name}; point_config_hash={point_version.config_hash}",
            f"robustness_model={version.model_name}; robustness_config_hash={version.config_hash}",
            f"zero_tolerance={robustness_config.tyre_slope_zero_tolerance} s/lap/lap",
        ),
    )
