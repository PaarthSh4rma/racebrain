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
    TyreCompound,
    TyreSlopeAvailabilityReason,
)
from app.domain_v2.estimates import TyreDegradationEstimate
from app.domain_v2.identity import CompetitorId, EventId, SessionId
from app.domain_v2.modelling import ModellingLapObservation, PaceEstimationContext, TyreSlopeModelConfig
from app.domain_v2.provenance import DataQuality
from app.domain_v2.race_state import CarState, Event, RaceState, Session
from app.domain_v2.tyre_slope import CompetitorTyreSlopeFit
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


def context(observations, competitors=(A,)):
    state = RaceState(
        session=Session(
            session_id=SessionId("race-1"),
            event=Event(event_id=EventId("event-1"), name="Test Grand Prix"),
            name="Race",
        ),
        observation_cutoff=NOW,
        competitors=tuple(CarState(competitor_id=item, observed_at=NOW) for item in competitors),
    )
    return PaceEstimationContext(
        race_state=state,
        as_of=NOW,
        observations=tuple(sorted(observations, key=lambda item: (str(item.competitor_id), item.lap_number))),
    )


def config(**updates):
    values = dict(
        model_name="empirical-tyre-age-slope",
        model_version="0.1.0",
        minimum_clean_laps=5,
        minimum_tyre_age_span_laps=4,
        excluded_quality_warnings=(LapQualityWarning.WEATHER_TRANSITION,),
    )
    values.update(updates)
    return TyreSlopeModelConfig(**values)


@pytest.mark.parametrize("slope", (-0.25, 0.0, 0.2))
def test_closed_form_ols_preserves_negative_zero_and_positive_empirical_slopes(slope):
    observations = [lap(lap_number=age, tyre_age_laps=age, lap_time_s=80 + slope * age) for age in (2, 3, 4, 5, 6)]
    fit = estimate_competitor_tyre_slope(context(observations), A, config())
    assert fit.estimate.value == pytest.approx(slope)
    assert fit.diagnostics.intercept_s == pytest.approx(80)
    assert fit.diagnostics.residual_median_s == pytest.approx(0)
    assert fit.diagnostics.residual_median_absolute_s == pytest.approx(0)
    assert fit.estimate.uncertainty is None
    assert fit.estimate.confidence is ConfidenceLevel.UNKNOWN


def test_latest_bounded_stint_is_selected_without_falling_back_or_pooling():
    observations = [
        *[lap(lap_number=value, tyre_age_laps=value, stint_number=1) for value in (2, 3, 4, 5, 6)],
        lap(lap_number=10, tyre_age_laps=1, stint_number=2, compound=TyreCompound.HARD),
        lap(lap_number=11, tyre_age_laps=2, stint_number=2, compound=TyreCompound.HARD),
    ]
    fit = estimate_competitor_tyre_slope(context(observations), A, config())
    assert fit.estimate is None
    assert fit.unavailable_reason is TyreSlopeAvailabilityReason.INSUFFICIENT_CLEAN_LAPS
    assert fit.diagnostics.stint_number == 2
    assert fit.diagnostics.compound is TyreCompound.HARD
    assert (fit.diagnostics.candidate_laps, fit.diagnostics.included_laps) == (2, 2)


def test_mixed_compound_in_selected_stint_is_rejected():
    observations = [
        lap(lap_number=2, compound=TyreCompound.MEDIUM),
        lap(lap_number=3, compound=TyreCompound.MEDIUM),
        lap(lap_number=4, compound=TyreCompound.HARD),
        lap(lap_number=5, compound=TyreCompound.HARD),
    ]
    fit = estimate_competitor_tyre_slope(context(observations), A, config())
    assert fit.estimate is None
    assert fit.unavailable_reason is TyreSlopeAvailabilityReason.MIXED_COMPOUND
    assert fit.diagnostics.excluded_laps == 4


@pytest.mark.parametrize(
    "update,reason",
    (
        ({"compound": None}, TyreSlopeAvailabilityReason.MISSING_TYRE_ANNOTATION),
        ({"tyre_age_laps": None}, TyreSlopeAvailabilityReason.MISSING_TYRE_ANNOTATION),
        ({"stint_number": None}, TyreSlopeAvailabilityReason.MISSING_TYRE_ANNOTATION),
        ({"compound": TyreCompound.UNKNOWN}, TyreSlopeAvailabilityReason.UNKNOWN_COMPOUND),
    ),
)
def test_latest_lap_requires_complete_identified_tyre_annotation(update, reason):
    latest = lap(lap_number=5).model_copy(update=update)
    fit = estimate_competitor_tyre_slope(
        context([lap(lap_number=value) for value in (2, 3, 4)] + [latest]), A, config(),
    )
    assert fit.estimate is None and fit.unavailable_reason is reason


def test_inconsistent_lap_for_lap_tyre_age_progression_is_rejected():
    observations = [
        lap(lap_number=2, tyre_age_laps=2),
        lap(lap_number=3, tyre_age_laps=3),
        lap(lap_number=4, tyre_age_laps=7),
        lap(lap_number=5, tyre_age_laps=8),
    ]
    fit = estimate_competitor_tyre_slope(context(observations), A, config())
    assert fit.unavailable_reason is TyreSlopeAvailabilityReason.INCONSISTENT_TYRE_AGE_PROGRESSION


def test_minimum_clean_count_and_age_span_are_separate_identifiability_gates():
    insufficient_count = estimate_competitor_tyre_slope(
        context([lap(lap_number=value) for value in (2, 3, 4)]), A, config(),
    )
    insufficient_span = estimate_competitor_tyre_slope(
        context([lap(lap_number=value) for value in (2, 3, 4, 5, 6)]),
        A,
        config(minimum_tyre_age_span_laps=5),
    )
    assert insufficient_count.unavailable_reason is TyreSlopeAvailabilityReason.INSUFFICIENT_CLEAN_LAPS
    assert insufficient_span.unavailable_reason is TyreSlopeAvailabilityReason.INSUFFICIENT_TYRE_AGE_SPAN


def test_hard_and_configured_warning_exclusions_are_audited_without_double_counting_laps():
    observations = [lap(lap_number=value, lap_time_s=80 + value / 10) for value in range(2, 10)]
    observations[0] = observations[0].model_copy(update={
        "hard_exclusions": (LapExclusionReason.PIT_OUT, LapExclusionReason.SAFETY_CAR),
    })
    observations[1] = observations[1].model_copy(update={
        "hard_exclusions": (LapExclusionReason.PIT_OUT,),
        "quality_warnings": (LapQualityWarning.WEATHER_TRANSITION,),
    })
    fit = estimate_competitor_tyre_slope(context(observations), A, config())
    assert fit.estimate is not None
    assert (fit.diagnostics.candidate_laps, fit.diagnostics.included_laps, fit.diagnostics.excluded_laps) == (8, 6, 2)
    assert {item.reason: item.lap_count for item in fit.selection_audit.hard_exclusions} == {
        LapExclusionReason.PIT_OUT: 2,
        LapExclusionReason.SAFETY_CAR: 1,
    }
    assert fit.selection_audit.warning_exclusions[0].lap_count == 1


def test_nonconfigured_warning_and_degraded_quality_do_not_filter_laps():
    degraded = DataQuality(
        level=DataQualityLevel.DEGRADED,
        warnings=("OpenF1 lap completion is approximated from date_start + lap_duration",),
        missing_fields=("gap_context",),
    )
    observations = [
        lap(
            lap_number=value,
            quality=degraded,
            quality_warnings=(LapQualityWarning.TRAFFIC_SUSPECTED,),
        )
        for value in (2, 3, 4, 5, 6)
    ]
    fit = estimate_competitor_tyre_slope(context(observations), A, config())
    assert fit.estimate is not None and fit.diagnostics.included_laps == 5
    assert fit.estimate.data_quality.level is DataQualityLevel.DEGRADED
    assert fit.estimate.data_quality.missing_fields == ()
    assert fit.estimate.data_quality.completeness is None


def test_model_relevant_selection_quality_is_deterministic_without_filtering():
    timing = "OpenF1 lap completion is approximated from date_start + lap_duration"
    limited = DataQuality(
        warnings=(timing, timing),
        missing_fields=("weather_context", "gap_context", "race_control_context", "weather_context"),
    )
    observations = [lap(lap_number=value, quality=limited) for value in (2, 3, 4, 5, 6)]
    configured = estimate_competitor_tyre_slope(context(observations), A, config())
    no_weather_policy = estimate_competitor_tyre_slope(
        context(observations), A, config(excluded_quality_warnings=()),
    )
    assert configured.estimate.data_quality.missing_fields == ("race_control_context", "weather_context")
    assert configured.estimate.data_quality.warnings == (timing,)
    assert configured.estimate.data_quality.level is DataQualityLevel.DEGRADED
    assert configured.diagnostics.included_laps == 5
    assert no_weather_policy.estimate.data_quality.missing_fields == ("race_control_context",)
    assert no_weather_policy.diagnostics.included_laps == 5


def test_evidence_diagnostics_and_result_contract_reconcile():
    observations = [lap(lap_number=value, tyre_age_laps=value, lap_time_s=value * 2) for value in (2, 3, 4, 5, 6)]
    fit = estimate_competitor_tyre_slope(context(observations), A, config())
    assert fit.estimate.sample_count == fit.diagnostics.included_laps == 5
    assert (fit.estimate.minimum_tyre_age_laps, fit.estimate.maximum_tyre_age_laps) == (2, 6)
    assert fit.diagnostics.tyre_age_span_laps == 4
    assert (fit.estimate.evidence_window.first_lap, fit.estimate.evidence_window.last_lap) == (2, 6)
    assert CompetitorTyreSlopeFit.model_validate(fit.model_dump()) == fit
    bad = fit.estimate.model_copy(update={"sample_count": 4})
    with pytest.raises(ValidationError, match="sample count"):
        CompetitorTyreSlopeFit(
            competitor_id=A,
            estimate=bad,
            diagnostics=fit.diagnostics,
            selection_audit=fit.selection_audit,
        )
    with pytest.raises(ValidationError, match="identified compound"):
        TyreDegradationEstimate(**(fit.estimate.model_dump() | {"compound": TyreCompound.UNKNOWN}))


def test_full_field_result_is_ordered_and_keeps_explicit_unavailable_cars():
    observations = [
        *[lap(A, value, 80 + value / 10) for value in (2, 3, 4, 5, 6)],
        *[lap(B, value, 81 + value / 10) for value in (2, 3, 4, 5)],
    ]
    result = estimate_field_tyre_slopes(context(observations, competitors=(C, B, A)), config())
    assert tuple(item.competitor_id for item in result.competitors) == (A, B, C)
    by_id = {item.competitor_id: item for item in result.competitors}
    assert by_id[A].estimate is not None
    assert by_id[B].unavailable_reason is TyreSlopeAvailabilityReason.INSUFFICIENT_CLEAN_LAPS
    assert by_id[C].unavailable_reason is TyreSlopeAvailabilityReason.NO_OBSERVATIONS


def test_config_hash_is_deterministic_and_covers_every_parameter():
    baseline = config()
    assert baseline.version() == baseline.model_copy().version()
    assert baseline.version().config_hash != config(minimum_clean_laps=6).version().config_hash
    assert baseline.version().config_hash != config(minimum_tyre_age_span_laps=5).version().config_hash
    assert baseline.version().config_hash != config(excluded_quality_warnings=()).version().config_hash
    assert baseline.version().config_hash != config(model_version="0.1.1").version().config_hash
    with pytest.raises(ValidationError):
        config(excluded_quality_warnings=(LapQualityWarning.WEATHER_TRANSITION,) * 2)
    assert BASELINE_TYRE_SLOPE_CONFIG == baseline


def test_estimator_is_deterministic_immutable_and_has_no_provider_dependency():
    source = context([lap(lap_number=value) for value in (2, 3, 4, 5, 6)])
    before = source.model_copy(deep=True)
    assert estimate_field_tyre_slopes(source, config()) == estimate_field_tyre_slopes(source, config())
    assert source == before
    module_source = inspect.getsource(inspect.getmodule(estimate_field_tyre_slopes))
    assert "OpenF1" not in module_source and "app.adapters" not in module_source and "app.data_sources" not in module_source


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


def historical_estimate(payload, decision_lap):
    built = build_historical_pace_context(
        HistoricalRaceStateRequest(
            openf1_session_key=999,
            focal_driver_number=16,
            decision_lap=decision_lap,
        ),
        RecordingOpenF1Client(payload),
    )
    return built.context, estimate_field_tyre_slopes(built.context, config())


def test_future_provider_contamination_produces_identical_context_and_slope_result():
    clean = historical_payload_with_laps()
    dirty = deepcopy(clean)
    dirty["laps"].append({
        "session_key": 999, "driver_number": 16, "lap_number": 50,
        "date_start": "2024-05-26T14:00:00Z", "lap_duration": 50,
    })
    dirty["stints"].append({
        "session_key": 999, "driver_number": 16, "stint_number": 9,
        "lap_start": 50, "compound": "WET", "tyre_age_at_start": 20,
    })
    clean_context, clean_result = historical_estimate(clean, 5)
    dirty_context, dirty_result = historical_estimate(dirty, 5)
    assert clean_context == dirty_context
    assert clean_result == dirty_result


def test_cutoff_advance_recomputes_without_mutating_earlier_slope_result():
    payload = historical_payload_with_laps()
    early_context, early = historical_estimate(payload, 5)
    late_context, late = historical_estimate(payload, 6)
    frozen_early = early.model_copy(deep=True)
    assert early_context.as_of < late_context.as_of
    assert early == frozen_early
    assert early != late
