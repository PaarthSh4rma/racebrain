from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.domain_v2.enums import (
    LapExclusionReason,
    LapQualityWarning,
    PaceEstimateKind,
    TyreCompound,
)
from app.domain_v2.estimates import DegradationEstimate, EvidenceWindow, PaceEstimate, TyreDegradationEstimate
from app.domain_v2.identity import CompetitorId, EventId, SessionId
from app.domain_v2.modelling import (
    FitDiagnostics,
    ModellingLapObservation,
    PaceEstimationContext,
    PaceModelConfig,
)
from app.domain_v2.race_state import CarState, Event, RaceState, Session


NOW = datetime(2024, 6, 23, 14, 30, tzinfo=timezone.utc)
COMPETITOR = CompetitorId("entry-44")
CONFIG = PaceModelConfig(
    model_name="interpretable-pace-baseline",
    model_version="0.1.0",
    minimum_clean_laps=3,
)


def race_state() -> RaceState:
    return RaceState(
        session=Session(
            session_id=SessionId("race-spain-2024"),
            event=Event(event_id=EventId("spain-2024"), name="Spanish Grand Prix"),
            name="Race",
        ),
        observation_cutoff=NOW,
        competitors=(CarState(competitor_id=COMPETITOR, observed_at=NOW),),
    )


def observation(lap: int = 20, completed_at: datetime = NOW - timedelta(minutes=2)):
    return ModellingLapObservation(
        competitor_id=COMPETITOR,
        lap_number=lap,
        completed_at=completed_at,
        lap_time_s=78.432,
        compound=TyreCompound.MEDIUM,
        tyre_age_laps=12,
        stint_number=1,
    )


def evidence_window() -> EvidenceWindow:
    return EvidenceWindow(
        started_at=NOW - timedelta(minutes=20),
        ended_at=NOW - timedelta(minutes=2),
        first_lap=10,
        last_lap=20,
    )


def test_modelling_context_is_strict_immutable_and_cutoff_bounded():
    context = PaceEstimationContext(race_state=race_state(), as_of=NOW, observations=(observation(),))
    with pytest.raises(ValidationError):
        context.as_of = NOW + timedelta(seconds=1)
    with pytest.raises(ValidationError):
        PaceEstimationContext(race_state=race_state(), as_of=NOW, observations=(observation(completed_at=NOW + timedelta(seconds=1)),))
    with pytest.raises(ValidationError):
        ModellingLapObservation(**(observation().model_dump() | {"tyre_age_laps": -1}))


def test_provider_record_keys_cannot_replace_canonical_model_identity():
    with pytest.raises(ValidationError):
        ModellingLapObservation(**observation().model_dump(exclude={"competitor_id"}), competitor_id=44)


def test_closed_taxonomy_separates_observed_exclusions_from_suspicions():
    excluded = observation().model_copy(update={"hard_exclusions": (LapExclusionReason.PIT_OUT,)})
    warned = observation().model_copy(update={"quality_warnings": (LapQualityWarning.TRAFFIC_SUSPECTED,)})
    assert excluded.hard_exclusions == (LapExclusionReason.PIT_OUT,)
    assert warned.quality_warnings == (LapQualityWarning.TRAFFIC_SUSPECTED,)
    with pytest.raises(ValidationError):
        ModellingLapObservation(**(observation().model_dump() | {"hard_exclusions": ("dirty_air_proven",)}))


def test_model_config_hash_is_deterministic_and_sensitive_to_typed_config():
    assert CONFIG.version() == CONFIG.model_copy().version()
    changed = CONFIG.model_copy(update={"minimum_clean_laps": 4})
    assert CONFIG.version().config_hash != changed.version().config_hash


def test_pace_estimate_has_explicit_subject_cutoff_meaning_and_reference_rules():
    absolute = PaceEstimate(
        value=78.2,
        competitor_id=COMPETITOR,
        as_of=NOW,
        meaning=PaceEstimateKind.REPRESENTATIVE_CLEAN_LAP_TIME,
        sample_count=8,
        evidence_window=evidence_window(),
        model_version=CONFIG.version(),
    )
    assert absolute.unit == "s/lap"
    with pytest.raises(ValidationError):
        PaceEstimate(**(absolute.model_dump() | {"reference": "field median at cutoff"}))
    relative = PaceEstimate.model_validate(absolute.model_dump() | {
        "value": 0.18,
        "meaning": PaceEstimateKind.RELATIVE_TO_REFERENCE,
        "reference": "field median clean lap time at the same cutoff",
    })
    assert relative.reference is not None


def test_degradation_is_tyre_age_slope_with_explicit_units_and_range():
    assert DegradationEstimate is TyreDegradationEstimate
    estimate = DegradationEstimate(
        value=0.041,
        competitor_id=COMPETITOR,
        as_of=NOW,
        compound=TyreCompound.MEDIUM,
        minimum_tyre_age_laps=5,
        maximum_tyre_age_laps=16,
        sample_count=8,
        evidence_window=evidence_window(),
        model_version=CONFIG.version(),
        limitations=("Fuel burn and track evolution are not separately identified.",),
    )
    assert estimate.unit == "s/lap/lap"
    with pytest.raises(ValidationError):
        DegradationEstimate(**(estimate.model_dump() | {"minimum_tyre_age_laps": 17}))


def test_fit_diagnostics_counts_are_consistent_and_no_confidence_is_fabricated():
    diagnostics = FitDiagnostics(
        competitor_id=COMPETITOR,
        as_of=NOW,
        candidate_laps=10,
        included_laps=7,
        excluded_laps=3,
        model_version=CONFIG.version(),
    )
    assert "confidence" not in FitDiagnostics.model_fields
    with pytest.raises(ValidationError):
        FitDiagnostics(**(diagnostics.model_dump() | {"excluded_laps": 2}))
