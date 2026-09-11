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
    PaceAvailabilityReason,
)
from app.domain_v2.identity import CompetitorId, EventId, SessionId
from app.domain_v2.modelling import ModellingLapObservation, PaceEstimationContext, PaceModelConfig
from app.domain_v2.pace import CompetitorPaceFit
from app.domain_v2.provenance import DataQuality
from app.domain_v2.race_state import CarState, Event, RaceState, Session
from app.models_v2.representative_pace import (
    BASELINE_PACE_CONFIG,
    estimate_competitor_pace,
    estimate_field_pace,
)
from tests.fixtures.openf1_v2_fixtures import RecordingOpenF1Client, historical_payload


NOW = datetime(2024, 6, 23, 14, 0, tzinfo=timezone.utc)
A, B, C, D = (CompetitorId(f"entry-{value}") for value in "abcd")


def lap(
    competitor_id=A,
    lap_number=1,
    lap_time_s=80.0,
    hard_exclusions=(),
    quality_warnings=(),
    quality=DataQuality(level=DataQualityLevel.GOOD),
):
    return ModellingLapObservation(
        competitor_id=competitor_id,
        lap_number=lap_number,
        completed_at=NOW - timedelta(minutes=30 - lap_number),
        lap_time_s=lap_time_s,
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
        model_name="representative-clean-pace",
        model_version="0.1.0",
        lookback_laps=8,
        minimum_clean_laps=3,
        excluded_quality_warnings=(LapQualityWarning.WEATHER_TRANSITION,),
    )
    values.update(updates)
    return PaceModelConfig(**values)


@pytest.mark.parametrize("times,expected", [
    ((80.0, 81.0, 82.0), 81.0),
    ((80.0, 81.0, 82.0, 83.0), 81.5),
])
def test_standard_library_median_handles_odd_and_even_samples(times, expected):
    fit = estimate_competitor_pace(context([lap(lap_number=index + 10, lap_time_s=value) for index, value in enumerate(times)]), A, config())
    assert fit.estimate.value == expected
    assert fit.estimate.sample_count == fit.diagnostics.included_laps == len(times)
    assert fit.estimate.uncertainty is None
    assert fit.estimate.confidence is ConfidenceLevel.UNKNOWN


def test_hard_and_configured_warning_exclusions_do_not_enter_median_and_audit_overlaps():
    observations = [
        lap(lap_number=10, lap_time_s=80),
        lap(lap_number=11, lap_time_s=81),
        lap(lap_number=12, lap_time_s=82),
        lap(lap_number=13, lap_time_s=20, hard_exclusions=(LapExclusionReason.PIT_OUT, LapExclusionReason.SAFETY_CAR)),
        lap(
            lap_number=14, lap_time_s=200,
            hard_exclusions=(LapExclusionReason.PIT_OUT,),
            quality_warnings=(LapQualityWarning.WEATHER_TRANSITION,),
        ),
    ]
    fit = estimate_competitor_pace(context(observations), A, config())
    assert fit.estimate.value == 81
    assert (fit.diagnostics.candidate_laps, fit.diagnostics.included_laps, fit.diagnostics.excluded_laps) == (5, 3, 2)
    assert {item.reason: item.lap_count for item in fit.selection_audit.hard_exclusions} == {
        LapExclusionReason.PIT_OUT: 2,
        LapExclusionReason.SAFETY_CAR: 1,
    }
    assert fit.selection_audit.warning_exclusions[0].lap_count == 1


@pytest.mark.parametrize("reason", tuple(LapExclusionReason))
def test_every_factual_hard_exclusion_is_disqualifying(reason):
    observations = [
        lap(lap_number=10, lap_time_s=80),
        lap(lap_number=11, lap_time_s=81),
        lap(lap_number=12, lap_time_s=82),
        lap(lap_number=13, lap_time_s=1, hard_exclusions=(reason,)),
    ]
    fit = estimate_competitor_pace(context(observations), A, config())
    assert fit.estimate.value == 81
    assert fit.diagnostics.excluded_laps == 1
    assert fit.selection_audit.hard_exclusions[0].reason is reason


def test_nonconfigured_soft_warning_remains_eligible():
    observations = [
        lap(lap_number=10 + index, lap_time_s=value, quality_warnings=(LapQualityWarning.TRAFFIC_SUSPECTED,))
        for index, value in enumerate((80, 81, 82))
    ]
    fit = estimate_competitor_pace(context(observations), A, config())
    assert fit.estimate.value == 81 and fit.diagnostics.excluded_laps == 0


def test_trailing_window_uses_lap_numbers_and_does_not_stretch_for_missing_lap():
    observations = [lap(lap_number=12, lap_time_s=1)] + [
        lap(lap_number=value, lap_time_s=float(value)) for value in range(13, 21) if value != 16
    ]
    fit = estimate_competitor_pace(context(observations), A, config())
    assert fit.diagnostics.candidate_laps == 7
    assert fit.estimate.sample_count == 7
    assert fit.estimate.evidence_window.first_lap == 13
    assert fit.estimate.evidence_window.last_lap == 20
    assert fit.estimate.value == 17


def test_insufficient_clean_laps_return_no_estimate_without_expanding_window():
    observations = [
        lap(lap_number=12, lap_time_s=79),
        lap(lap_number=13, lap_time_s=80),
        lap(lap_number=14, lap_time_s=81, hard_exclusions=(LapExclusionReason.PIT_OUT,)),
        lap(lap_number=20, lap_time_s=82),
    ]
    fit = estimate_competitor_pace(context(observations), A, config(minimum_clean_laps=3))
    assert fit.estimate is None
    assert fit.unavailable_reason is PaceAvailabilityReason.INSUFFICIENT_RECENT_CLEAN_LAPS
    assert (fit.diagnostics.candidate_laps, fit.diagnostics.included_laps, fit.diagnostics.excluded_laps) == (3, 2, 1)
    assert fit.diagnostics.data_quality.level is DataQualityLevel.INSUFFICIENT


def test_evidence_window_and_residual_median_absolute_use_only_included_laps():
    observations = [
        lap(lap_number=10, lap_time_s=80),
        lap(lap_number=11, lap_time_s=81),
        lap(lap_number=12, lap_time_s=100, hard_exclusions=(LapExclusionReason.PIT_OUT,)),
        lap(lap_number=13, lap_time_s=84),
    ]
    fit = estimate_competitor_pace(context(observations), A, config())
    assert fit.estimate.value == 81
    assert (fit.estimate.evidence_window.first_lap, fit.estimate.evidence_window.last_lap) == (10, 13)
    assert fit.estimate.evidence_window.started_at == observations[0].completed_at
    assert fit.estimate.evidence_window.ended_at == observations[3].completed_at
    assert fit.diagnostics.residual_median_s == 0
    assert fit.diagnostics.residual_median_absolute_s == 1


def test_degraded_timing_evidence_is_eligible_but_estimate_quality_remains_degraded():
    degraded = DataQuality(
        level=DataQualityLevel.DEGRADED,
        warnings=("OpenF1 lap completion is approximated from date_start + lap_duration",),
    )
    fit = estimate_competitor_pace(
        context([lap(lap_number=index, lap_time_s=80 + index, quality=degraded) for index in (1, 2, 3)]),
        A,
        config(),
    )
    assert fit.estimate is not None and fit.diagnostics.included_laps == 3
    assert fit.estimate.data_quality.level is DataQualityLevel.DEGRADED
    assert fit.estimate.data_quality.completeness is None
    assert fit.estimate.data_quality.missing_fields == ()


def test_full_field_result_includes_available_insufficient_empty_and_excluded_competitors_in_order():
    observations = [
        *[lap(A, index, 80 + index) for index in (1, 2, 3)],
        *[lap(B, index, 80 + index) for index in (1, 2)],
        *[lap(D, index, 80 + index, hard_exclusions=(LapExclusionReason.PIT_OUT,)) for index in (1, 2, 3)],
    ]
    result = estimate_field_pace(context(observations, competitors=(D, C, B, A)), config())
    assert tuple(item.competitor_id for item in result.competitors) == tuple(sorted((A, B, C, D), key=str))
    by_id = {item.competitor_id: item for item in result.competitors}
    assert by_id[A].estimate is not None
    assert by_id[B].diagnostics.included_laps == 2 and by_id[B].estimate is None
    assert by_id[C].diagnostics.candidate_laps == 0 and by_id[C].estimate is None
    assert by_id[D].diagnostics.excluded_laps == 3 and by_id[D].estimate is None
    assert result.as_of == NOW
    assert all(item.diagnostics.as_of == result.as_of for item in result.competitors)


def test_config_hash_covers_lookback_warning_policy_and_version_with_canonical_warning_order():
    baseline = config()
    assert baseline.version().config_hash != config(lookback_laps=5).version().config_hash
    assert baseline.version().config_hash != config(excluded_quality_warnings=()).version().config_hash
    assert baseline.version().config_hash != config(model_version="0.1.1").version().config_hash
    reordered = config(excluded_quality_warnings=(LapQualityWarning.EXTREME_OUTLIER, LapQualityWarning.WEATHER_TRANSITION))
    canonical = config(excluded_quality_warnings=(LapQualityWarning.WEATHER_TRANSITION, LapQualityWarning.EXTREME_OUTLIER))
    assert reordered.version() == canonical.version()


@pytest.mark.parametrize("lookback,minimum", ((8, 3), (3, 3)))
def test_config_accepts_lookback_that_can_satisfy_minimum_clean_laps(lookback, minimum):
    assert config(lookback_laps=lookback, minimum_clean_laps=minimum).lookback_laps == lookback


def test_config_rejects_minimum_clean_laps_larger_than_lookback():
    with pytest.raises(ValidationError, match="lookback_laps must be greater than or equal"):
        config(lookback_laps=2, minimum_clean_laps=3)


def test_fit_contract_accepts_matching_and_rejects_mismatched_sample_count():
    fit = estimate_competitor_pace(
        context([lap(lap_number=index, lap_time_s=80 + index) for index in (1, 2, 3)]),
        A,
        config(),
    )
    assert CompetitorPaceFit.model_validate(fit.model_dump()) == fit
    mismatched = fit.estimate.model_copy(update={"sample_count": fit.estimate.sample_count + 1})
    with pytest.raises(ValidationError, match="sample count must equal"):
        CompetitorPaceFit(
            competitor_id=fit.competitor_id,
            estimate=mismatched,
            diagnostics=fit.diagnostics,
            selection_audit=fit.selection_audit,
        )


def test_missing_race_control_selection_evidence_degrades_without_excluding():
    missing = DataQuality(missing_fields=("race_control_context",))
    fit = estimate_competitor_pace(
        context([lap(lap_number=index, lap_time_s=80 + index, quality=missing) for index in (1, 2, 3)]),
        A,
        config(),
    )
    assert (fit.diagnostics.candidate_laps, fit.diagnostics.included_laps, fit.diagnostics.excluded_laps) == (3, 3, 0)
    assert fit.estimate.data_quality.level is DataQualityLevel.DEGRADED
    assert fit.estimate.data_quality.missing_fields == ("race_control_context",)
    assert fit.diagnostics.data_quality.missing_fields == ("race_control_context",)
    assert fit.estimate.data_quality.completeness is None


def test_missing_weather_is_relevant_only_when_weather_transition_is_excluded():
    missing = DataQuality(missing_fields=("weather_context",))
    observations = [lap(lap_number=index, lap_time_s=80 + index, quality=missing) for index in (1, 2, 3)]
    configured = estimate_competitor_pace(context(observations), A, config())
    unconfigured = estimate_competitor_pace(
        context(observations), A, config(excluded_quality_warnings=()),
    )
    assert configured.estimate.data_quality.level is DataQualityLevel.DEGRADED
    assert configured.estimate.data_quality.missing_fields == ("weather_context",)
    assert configured.diagnostics.included_laps == 3
    assert unconfigured.estimate.data_quality.level is DataQualityLevel.GOOD
    assert unconfigured.estimate.data_quality.missing_fields == ()


@pytest.mark.parametrize("irrelevant", ("gap_context", "tyre_annotation"))
def test_missing_non_model_evidence_does_not_degrade_or_change_selection(irrelevant):
    missing = DataQuality(level=DataQualityLevel.DEGRADED, missing_fields=(irrelevant,))
    fit = estimate_competitor_pace(
        context([lap(lap_number=index, lap_time_s=80 + index, quality=missing) for index in (1, 2, 3)]),
        A,
        config(),
    )
    assert fit.estimate.data_quality.level is DataQualityLevel.GOOD
    assert fit.estimate.data_quality.missing_fields == ()
    assert (fit.diagnostics.candidate_laps, fit.diagnostics.included_laps, fit.diagnostics.excluded_laps) == (3, 3, 0)


def test_insufficient_quality_preserves_unique_deterministic_relevant_limitations():
    timing_warning = "OpenF1 lap completion is approximated from date_start + lap_duration"
    limited = DataQuality(
        warnings=(timing_warning, timing_warning),
        missing_fields=("weather_context", "race_control_context", "weather_context"),
    )
    fit = estimate_competitor_pace(
        context([lap(lap_number=index, lap_time_s=80 + index, quality=limited) for index in (1, 2)]),
        A,
        config(),
    )
    assert fit.estimate is None
    assert fit.diagnostics.data_quality.level is DataQualityLevel.INSUFFICIENT
    assert fit.diagnostics.data_quality.missing_fields == ("race_control_context", "weather_context")
    assert fit.diagnostics.data_quality.warnings == (
        timing_warning,
        "insufficient recent clean laps: 2 available; 3 required",
    )
    assert fit.diagnostics.data_quality.completeness is None
    assert (fit.diagnostics.candidate_laps, fit.diagnostics.included_laps, fit.diagnostics.excluded_laps) == (2, 2, 0)


def test_estimator_is_deterministic_pure_and_has_no_provider_dependency():
    source_context = context([lap(lap_number=index, lap_time_s=80 + index) for index in (1, 2, 3)])
    before = source_context.model_copy(deep=True)
    assert estimate_field_pace(source_context, config()) == estimate_field_pace(source_context, config())
    assert source_context == before
    source = inspect.getsource(inspect.getmodule(estimate_field_pace))
    assert "OpenF1" not in source and "app.adapters" not in source and "app.data_sources" not in source


def _historical_estimate(payload, decision_lap=2):
    context_result = build_historical_pace_context(
        HistoricalRaceStateRequest(openf1_session_key=999, focal_driver_number=16, decision_lap=decision_lap),
        RecordingOpenF1Client(payload),
    )
    return context_result.context, estimate_field_pace(context_result.context, config(minimum_clean_laps=2))


def test_future_provider_contamination_produces_identical_context_and_estimate():
    clean = historical_payload()
    dirty = deepcopy(clean)
    dirty["laps"].append({"session_key": 999, "driver_number": 16, "lap_number": 50, "date_start": "2024-05-26T14:00:00Z", "lap_duration": 60})
    dirty["weather"].append({"session_key": 999, "date": "2024-05-26T14:00:00Z", "rainfall": 1})
    clean_context, clean_result = _historical_estimate(clean)
    dirty_context, dirty_result = _historical_estimate(dirty)
    assert clean_context == dirty_context
    assert clean_result == dirty_result


def test_cutoff_advance_can_change_rolling_estimate_without_mutating_earlier_result():
    payload = historical_payload()
    for number, duration in ((3, 70), (4, 80)):
        payload["laps"].append({
            "session_key": 999, "driver_number": 16, "lap_number": number,
            "date_start": f"2024-05-26T13:0{number - 1}:00Z", "lap_duration": duration,
        })
    early_context, early = _historical_estimate(payload, decision_lap=3)
    late_context, late = _historical_estimate(payload, decision_lap=4)
    frozen_early = early.model_copy(deep=True)
    assert early_context.as_of < late_context.as_of
    assert early == frozen_early
    assert early != late


def test_approved_baseline_configuration_is_explicit():
    assert BASELINE_PACE_CONFIG == config()
