from copy import deepcopy
from datetime import datetime, timedelta, timezone
import inspect

import pytest
from pydantic import ValidationError

from app.application_v2.build_pace_context import build_historical_pace_context
from app.application_v2.reconstruct_race_state import HistoricalRaceStateRequest
from app.domain_v2.enums import (
    ConfidenceLevel,
    DataQualityLevel,
    LapExclusionReason,
    LapQualityWarning,
    PaceQuantileMethod,
    RobustnessAvailabilityReason,
    SlopeSign,
    TyreCompound,
    TyreSlopeAvailabilityReason,
)
from app.domain_v2.identity import CompetitorId, EventId, SessionId
from app.domain_v2.modelling import ModelRobustnessConfig, ModellingLapObservation, PaceEstimationContext
from app.domain_v2.provenance import DataQuality, Provenance
from app.domain_v2.race_state import CarState, Event, RaceState, Session
from app.domain_v2.robustness import PaceRobustnessResult, TyreSlopeRobustnessDiagnostics
from app.models_v2.model_robustness import (
    BASELINE_ROBUSTNESS_CONFIG,
    SENSITIVITY_ENVELOPE_METHOD,
    analyze_competitor_pace_robustness,
    analyze_competitor_tyre_slope_robustness,
    analyze_field_pace_robustness,
    analyze_field_tyre_slope_robustness,
    classify_slope_sign,
)
from app.models_v2.representative_pace import (
    BASELINE_PACE_CONFIG,
    estimate_competitor_pace,
    estimate_field_pace,
)
from app.models_v2.tyre_age_slope import (
    BASELINE_TYRE_SLOPE_CONFIG,
    estimate_competitor_tyre_slope,
    estimate_field_tyre_slopes,
)
from tests.fixtures.openf1_v2_fixtures import RecordingOpenF1Client, historical_payload


NOW = datetime(2024, 6, 23, 14, 30, tzinfo=timezone.utc)
A, B, C = (CompetitorId(f"entry-{value}") for value in "abc")


def lap(
    competitor_id=A,
    lap_number=2,
    lap_time_s=80.0,
    *,
    compound=TyreCompound.MEDIUM,
    tyre_age_laps=None,
    stint_number=1,
    hard_exclusions=(),
    quality_warnings=(),
    quality=DataQuality(level=DataQualityLevel.GOOD),
):
    return ModellingLapObservation(
        competitor_id=competitor_id,
        lap_number=lap_number,
        completed_at=NOW - timedelta(minutes=100 - lap_number),
        lap_time_s=lap_time_s,
        compound=compound,
        tyre_age_laps=lap_number if tyre_age_laps is None else tyre_age_laps,
        stint_number=stint_number,
        hard_exclusions=hard_exclusions,
        quality_warnings=quality_warnings,
        data_quality=quality,
    )


def context(observations, competitors=(A,), *, cutoff=NOW):
    state = RaceState(
        session=Session(
            session_id=SessionId("race-1"),
            event=Event(event_id=EventId("event-1"), name="Test Grand Prix"),
            name="Race",
        ),
        observation_cutoff=cutoff,
        competitors=tuple(CarState(competitor_id=item, observed_at=cutoff) for item in competitors),
    )
    return PaceEstimationContext(
        race_state=state,
        as_of=cutoff,
        observations=tuple(sorted(observations, key=lambda item: (str(item.competitor_id), item.lap_number))),
    )


def robustness_config(**updates):
    values = dict(
        model_name="empirical-model-robustness",
        model_version="0.1.0",
        pace_quantiles=(0.1, 0.5, 0.9),
        pace_quantile_method=PaceQuantileMethod.LINEAR_INTERPOLATION,
        tyre_slope_zero_tolerance=1e-9,
    )
    values.update(updates)
    return ModelRobustnessConfig(**values)


def tyre_analysis(times, **kwargs):
    observations = [
        lap(lap_number=index + 2, tyre_age_laps=index + 2, lap_time_s=value)
        for index, value in enumerate(times)
    ]
    return analyze_competitor_tyre_slope_robustness(context(observations), A, **kwargs)


def test_known_odd_sample_has_documented_linear_interpolated_quantiles_and_median():
    observations = [lap(lap_number=index + 10, lap_time_s=value) for index, value in enumerate((80, 81, 82, 83, 84))]
    result = analyze_competitor_pace_robustness(context(observations), A)
    assert result.diagnostics.quantiles.model_dump() == {
        "p10": 80.4,
        "p50": 82.0,
        "p90": 83.6,
        "sample_count": 5,
    }
    assert result.diagnostics.minimum_lap_time_s == 80
    assert result.diagnostics.maximum_lap_time_s == 84
    assert result.diagnostics.quantile_method is PaceQuantileMethod.LINEAR_INTERPOLATION
    assert result.diagnostics.p90_p10_spread_s == pytest.approx(3.2)
    assert result.diagnostics.quantiles.p10 <= result.diagnostics.quantiles.p50 <= result.diagnostics.quantiles.p90


def test_even_sample_p50_exactly_matches_accepted_median_despite_rounding_order():
    lower, upper = 60.0251, 125.116058
    midpoint = (lower + upper) / 2
    assert midpoint != lower + (upper - lower) * 0.5
    values = (55.0, lower, upper, 130.0)
    source = context([
        lap(lap_number=index + 10, lap_time_s=value)
        for index, value in enumerate(values)
    ])
    point_fit = estimate_competitor_pace(source, A)
    result = analyze_competitor_pace_robustness(source, A)

    assert result.point_fit == point_fit
    assert result.diagnostics.quantiles.sample_count == point_fit.estimate.sample_count == 4
    assert result.diagnostics.quantiles.p50 == result.point_fit.estimate.value == midpoint
    assert result.diagnostics.quantiles.p10 == values[0] + (values[1] - values[0]) * (3 * 0.1)
    assert result.diagnostics.quantiles.p90 == values[2] + (values[3] - values[2]) * (3 * 0.9 - 2)
    assert PaceRobustnessResult.model_validate(result.model_dump()) == result


def test_pace_quantiles_use_only_exact_included_hard_and_warning_filtered_laps():
    observations = [lap(lap_number=index, lap_time_s=value) for index, value in enumerate((80, 81, 82, 83, 84), 10)]
    observations += [
        lap(lap_number=15, lap_time_s=40, hard_exclusions=(LapExclusionReason.PIT_OUT,)),
        lap(lap_number=16, lap_time_s=120, quality_warnings=(LapQualityWarning.WEATHER_TRANSITION,)),
    ]
    result = analyze_competitor_pace_robustness(context(observations), A)
    assert result.diagnostics.quantiles.sample_count == result.point_fit.estimate.sample_count == 5
    assert result.diagnostics.minimum_lap_time_s == 80
    assert result.diagnostics.maximum_lap_time_s == 84
    assert result.point_fit.diagnostics.excluded_laps == 2


def test_pace_point_result_and_model_identity_are_exactly_unchanged():
    source = context([lap(lap_number=index, lap_time_s=80 + index / 10) for index in range(2, 10)])
    before = estimate_competitor_pace(source, A)
    result = analyze_competitor_pace_robustness(source, A)
    after = estimate_competitor_pace(source, A)
    assert result.point_fit == before == after
    assert result.point_model_version == BASELINE_PACE_CONFIG.version()
    assert result.point_fit.estimate.uncertainty is None
    assert result.point_fit.estimate.confidence is ConfidenceLevel.UNKNOWN
    assert result.diagnostics.quantiles.p50 == result.point_fit.estimate.value


def test_unavailable_pace_point_produces_unavailable_robustness_without_lowering_gate():
    result = analyze_competitor_pace_robustness(context([lap(lap_number=2), lap(lap_number=3)]), A)
    assert result.point_fit.estimate is None
    assert result.diagnostics is None
    assert result.unavailable_reason is RobustnessAvailabilityReason.POINT_ESTIMATE_UNAVAILABLE
    assert result.point_fit.unavailable_reason is not None


def test_pace_analysis_is_deterministic_immutable_and_provider_independent():
    source = context([lap(lap_number=index, lap_time_s=80 + index) for index in (2, 3, 4)])
    frozen = source.model_copy(deep=True)
    assert analyze_field_pace_robustness(source) == analyze_field_pace_robustness(source)
    assert source == frozen
    module = inspect.getmodule(analyze_field_pace_robustness)
    text = inspect.getsource(module)
    assert "OpenF1" not in text and "app.adapters" not in text and "app.data_sources" not in text


def test_pace_field_result_is_canonically_ordered_and_keeps_unavailable_cars():
    observations = [lap(A, index, 80 + index) for index in (2, 3, 4)]
    result = analyze_field_pace_robustness(context(observations, competitors=(C, B, A)))
    assert tuple(item.competitor_id for item in result.competitors) == (A, B, C)
    assert result.competitors[0].diagnostics is not None
    assert all(
        item.unavailable_reason is RobustnessAvailabilityReason.POINT_ESTIMATE_UNAVAILABLE
        for item in result.competitors[1:]
    )


def test_pace_robustness_preserves_point_data_quality_and_has_bounded_provenance():
    quality = DataQuality(
        level=DataQualityLevel.DEGRADED,
        warnings=("lap completion timing is approximate",),
        missing_fields=("race_control_context",),
    )
    source = context([lap(lap_number=index, quality=quality) for index in (2, 3, 4)])
    result = analyze_competitor_pace_robustness(source, A)
    assert result.data_quality == result.point_fit.estimate.data_quality
    assert result.data_quality.completeness is None
    assert result.provenance[0].observed_at is None
    assert "non-probabilistic" in result.provenance[0].assumptions[-1]
    values = {name: getattr(result, name) for name in type(result).model_fields}
    values["provenance"] = (Provenance(source="future", observed_at=NOW + timedelta(seconds=1)),)
    with pytest.raises(ValidationError, match="after its cutoff"):
        PaceRobustnessResult(**values)


def test_robustness_config_hash_is_deterministic_and_covers_tolerance_and_version():
    baseline = robustness_config()
    assert baseline == BASELINE_ROBUSTNESS_CONFIG
    assert baseline.version() == baseline.model_copy().version()
    assert baseline.version().config_hash == "sha256:f1728939dc8ff5ae30e23a0fbcc06dff2c2b44b4cb47e58d9dd5599d9d0b8032"
    assert baseline.version().config_hash != robustness_config(tyre_slope_zero_tolerance=1e-8).version().config_hash
    assert baseline.version().config_hash != robustness_config(model_version="0.1.1").version().config_hash
    with pytest.raises(ValidationError, match="fixed p10"):
        robustness_config(pace_quantiles=(0.2, 0.5, 0.8))
    with pytest.raises(ValidationError):
        robustness_config(tyre_slope_zero_tolerance=-1e-9)


@pytest.mark.parametrize(
    "slope,expected_sign",
    ((0.2, SlopeSign.POSITIVE), (-0.2, SlopeSign.NEGATIVE), (0.0, SlopeSign.ZERO)),
)
def test_perfect_linear_tyre_cohorts_are_sign_stable(slope, expected_sign):
    result = tyre_analysis(tuple(80 + slope * age for age in range(2, 7)))
    diagnostics = result.diagnostics
    assert diagnostics.nominal_slope_s_per_lap_per_lap == pytest.approx(slope)
    assert diagnostics.nominal_sign is expected_sign
    assert diagnostics.sign_stable is True
    assert diagnostics.leave_one_out_refit_count == 5
    assert all(item.sign is expected_sign for item in diagnostics.leave_one_out_refits)
    assert diagnostics.sensitivity_envelope.coverage is None
    assert diagnostics.sensitivity_envelope.method == SENSITIVITY_ENVELOPE_METHOD


def test_high_leverage_observation_can_flip_sign_without_changing_nominal_slope():
    result = tyre_analysis((75, 75, 77, 76, 75))
    diagnostics = result.diagnostics
    assert diagnostics.nominal_slope_s_per_lap_per_lap == pytest.approx(0.1)
    assert diagnostics.nominal_sign is SlopeSign.POSITIVE
    assert diagnostics.leave_one_out_min_s_per_lap_per_lap == pytest.approx(-0.1)
    assert diagnostics.sign_counts.negative == 1
    assert diagnostics.sign_stable is False


def test_leave_one_out_zero_classification_makes_nonzero_nominal_sign_unstable():
    result = tyre_analysis((75, 75, 75, 75, 76))
    diagnostics = result.diagnostics
    assert diagnostics.nominal_sign is SlopeSign.POSITIVE
    assert diagnostics.leave_one_out_refits[-1].slope_s_per_lap_per_lap == 0
    assert diagnostics.leave_one_out_refits[-1].sign is SlopeSign.ZERO
    assert diagnostics.sign_stable is False


def test_sensitivity_envelope_deviation_and_influential_lap_are_exact():
    result = tyre_analysis((75, 75, 77, 76, 75))
    diagnostics = result.diagnostics
    slopes = tuple(item.slope_s_per_lap_per_lap for item in diagnostics.leave_one_out_refits)
    assert diagnostics.sensitivity_envelope.lower == min(diagnostics.nominal_slope_s_per_lap_per_lap, *slopes)
    assert diagnostics.sensitivity_envelope.upper == max(diagnostics.nominal_slope_s_per_lap_per_lap, *slopes)
    assert diagnostics.maximum_absolute_deviation_s_per_lap_per_lap == pytest.approx(0.4)
    assert diagnostics.most_influential_omitted_lap == 6


def test_influential_lap_ties_use_lowest_canonical_lap_number():
    diagnostics = tyre_analysis((82, 83, 84, 85, 86)).diagnostics
    assert diagnostics.maximum_absolute_deviation_s_per_lap_per_lap == 0
    assert diagnostics.most_influential_omitted_lap == 2


def test_tyre_point_result_model_hash_and_negative_slope_are_exactly_unchanged():
    source = context([lap(lap_number=age, tyre_age_laps=age, lap_time_s=80 - 0.25 * age) for age in range(2, 7)])
    before = estimate_competitor_tyre_slope(source, A)
    result = analyze_competitor_tyre_slope_robustness(source, A)
    after = estimate_competitor_tyre_slope(source, A)
    assert result.point_fit == before == after
    assert result.point_model_version == BASELINE_TYRE_SLOPE_CONFIG.version()
    assert result.point_fit.estimate.value == pytest.approx(-0.25)
    assert result.point_fit.estimate.uncertainty is None
    assert result.point_fit.estimate.confidence is ConfidenceLevel.UNKNOWN


def test_unavailable_latest_stint_remains_unavailable_without_fallback_or_pooling():
    observations = [
        *[lap(lap_number=age, tyre_age_laps=age, stint_number=1) for age in range(2, 7)],
        lap(lap_number=10, tyre_age_laps=1, stint_number=2, compound=TyreCompound.HARD),
        lap(lap_number=11, tyre_age_laps=2, stint_number=2, compound=TyreCompound.HARD),
    ]
    result = analyze_competitor_tyre_slope_robustness(context(observations), A)
    assert result.diagnostics is None
    assert result.unavailable_reason is RobustnessAvailabilityReason.POINT_ESTIMATE_UNAVAILABLE
    assert result.point_fit.unavailable_reason is TyreSlopeAvailabilityReason.INSUFFICIENT_CLEAN_LAPS
    assert result.point_fit.diagnostics.stint_number == 2
    assert result.point_fit.diagnostics.included_laps == 2


def test_tyre_robustness_uses_only_point_included_laps_and_does_not_reapply_five_lap_gate():
    observations = [lap(lap_number=age, tyre_age_laps=age, lap_time_s=80 + age) for age in range(2, 9)]
    observations[0] = observations[0].model_copy(update={"hard_exclusions": (LapExclusionReason.PIT_OUT,)})
    observations[1] = observations[1].model_copy(update={"quality_warnings": (LapQualityWarning.WEATHER_TRANSITION,)})
    result = analyze_competitor_tyre_slope_robustness(context(observations), A)
    assert result.point_fit.estimate.sample_count == 5
    assert result.diagnostics.leave_one_out_refit_count == 5
    assert {item.omitted_lap_number for item in result.diagnostics.leave_one_out_refits} == {4, 5, 6, 7, 8}


def test_mathematically_invalid_diagnostic_refit_is_explicitly_unavailable():
    point_config = BASELINE_TYRE_SLOPE_CONFIG.__class__(
        model_name=BASELINE_TYRE_SLOPE_CONFIG.model_name,
        model_version=BASELINE_TYRE_SLOPE_CONFIG.model_version,
        minimum_clean_laps=2,
        minimum_tyre_age_span_laps=1,
        excluded_quality_warnings=BASELINE_TYRE_SLOPE_CONFIG.excluded_quality_warnings,
    )
    source = context([
        lap(lap_number=2, tyre_age_laps=2, lap_time_s=80),
        lap(lap_number=3, tyre_age_laps=3, lap_time_s=81),
    ])
    result = analyze_competitor_tyre_slope_robustness(source, A, point_config=point_config)
    assert result.point_fit.estimate is not None
    assert result.diagnostics is None
    assert result.unavailable_reason is RobustnessAvailabilityReason.INVALID_DIAGNOSTIC_REFIT
    assert "mathematically invalid OLS refit" in result.limitations[-1]


def test_tyre_robustness_is_deterministic_immutable_and_provider_independent():
    source = context([lap(lap_number=age, tyre_age_laps=age, lap_time_s=80 + age / 10) for age in range(2, 7)])
    frozen = source.model_copy(deep=True)
    assert analyze_field_tyre_slope_robustness(source) == analyze_field_tyre_slope_robustness(source)
    assert source == frozen
    text = inspect.getsource(inspect.getmodule(analyze_field_tyre_slope_robustness))
    assert "OpenF1" not in text and "app.adapters" not in text and "app.data_sources" not in text


def test_tyre_field_result_is_ordered_and_preserves_unavailable_results():
    observations = [lap(A, age, 80 + age / 10, tyre_age_laps=age) for age in range(2, 7)]
    result = analyze_field_tyre_slope_robustness(context(observations, competitors=(C, B, A)))
    assert tuple(item.competitor_id for item in result.competitors) == (A, B, C)
    assert result.competitors[0].diagnostics is not None
    assert all(
        item.unavailable_reason is RobustnessAvailabilityReason.POINT_ESTIMATE_UNAVAILABLE
        for item in result.competitors[1:]
    )


def test_tyre_robustness_preserves_data_quality_and_contract_reconciliation():
    quality = DataQuality(
        level=DataQualityLevel.DEGRADED,
        warnings=("lap duration timing is approximate",),
        missing_fields=("race_control_context",),
    )
    observations = [lap(lap_number=age, lap_time_s=80 + age / 10, quality=quality) for age in range(2, 7)]
    result = analyze_competitor_tyre_slope_robustness(context(observations), A)
    assert result.data_quality == result.point_fit.estimate.data_quality
    assert result.data_quality.completeness is None
    assert result.provenance[0].observed_at is None
    assert "zero_tolerance=1e-09" in result.provenance[0].assumptions[-1]
    assert result.diagnostics.zero_tolerance_s_per_lap_per_lap == 1e-9
    assert TyreSlopeRobustnessDiagnostics.model_validate(result.diagnostics.model_dump()) == result.diagnostics
    values = {name: getattr(result.diagnostics, name) for name in type(result.diagnostics).model_fields}
    values["sign_stable"] = not result.diagnostics.sign_stable
    with pytest.raises(ValidationError, match="Sign stability|sign stability"):
        TyreSlopeRobustnessDiagnostics(**values)


@pytest.mark.parametrize(
    "slope,expected",
    (
        (1e-9, SlopeSign.ZERO),
        (-1e-9, SlopeSign.ZERO),
        (1.000001e-9, SlopeSign.POSITIVE),
        (-1.000001e-9, SlopeSign.NEGATIVE),
    ),
)
def test_zero_tolerance_boundaries_are_inclusive(slope, expected):
    assert classify_slope_sign(slope, 1e-9) is expected


def historical_payload_with_laps():
    payload = historical_payload()
    payload["weather"] = payload["weather"][:1]
    payload["race_control"] = payload["race_control"][:1]
    for number, duration in ((3, 61), (4, 62), (5, 63), (6, 70)):
        payload["laps"].append({
            "session_key": 999,
            "driver_number": 16,
            "lap_number": number,
            "date_start": f"2024-05-26T13:0{number - 1}:00Z",
            "lap_duration": duration,
        })
    return payload


def historical_outputs(payload, decision_lap):
    built = build_historical_pace_context(
        HistoricalRaceStateRequest(
            openf1_session_key=999,
            focal_driver_number=16,
            decision_lap=decision_lap,
        ),
        RecordingOpenF1Client(payload),
    )
    source = built.context
    return (
        source,
        estimate_field_pace(source),
        estimate_field_tyre_slopes(source),
        analyze_field_pace_robustness(source),
        analyze_field_tyre_slope_robustness(source),
    )


def test_future_provider_contamination_cannot_change_context_points_or_robustness():
    clean = historical_payload_with_laps()
    dirty = deepcopy(clean)
    dirty["laps"].append({
        "session_key": 999,
        "driver_number": 16,
        "lap_number": 50,
        "date_start": "2024-05-26T14:00:00Z",
        "lap_duration": 50,
    })
    dirty["stints"].append({
        "session_key": 999,
        "driver_number": 16,
        "stint_number": 9,
        "lap_start": 50,
        "compound": "WET",
        "tyre_age_at_start": 20,
    })
    dirty["weather"].append({"session_key": 999, "date": "2024-05-26T14:00:00Z", "rainfall": 1})
    assert historical_outputs(clean, 5) == historical_outputs(dirty, 5)


def test_cutoff_advance_reanalyzes_only_later_context_without_mutating_early_result():
    payload = historical_payload_with_laps()
    early = historical_outputs(payload, 5)
    frozen_early = tuple(item.model_copy(deep=True) for item in early)
    late = historical_outputs(payload, 6)
    assert early == frozen_early
    assert early[0].as_of < late[0].as_of
    assert early != late
    assert all(item.completed_at <= early[0].as_of for item in early[0].observations)
    assert all(item.completed_at <= late[0].as_of for item in late[0].observations)
