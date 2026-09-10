from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.domain_v2.enums import (
    LapAdmissionRejectionReason,
    LapExclusionReason,
    LapQualityWarning,
    TrackStatus,
    TyreCompound,
)
from app.domain_v2.estimates import DegradationEstimate, EvidenceWindow, PaceEstimate, TyreDegradationEstimate
from app.domain_v2.identity import CompetitorId, EventId, SessionId
from app.domain_v2.modelling import (
    FitDiagnostics,
    GapEvidence,
    ModellingLapObservation,
    PaceEstimationContext,
    PaceModelConfig,
    TrackStatusEvidence,
)
from app.domain_v2.provenance import Provenance
from app.domain_v2.race_state import CarState, Event, RaceState, Session, WeatherState


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


def test_closed_taxonomy_separates_admission_rejection_exclusion_and_suspicion():
    assert set(LapAdmissionRejectionReason) == {
        LapAdmissionRejectionReason.MISSING_TIMING,
        LapAdmissionRejectionReason.INVALID_DURATION,
    }
    assert "missing_timing" not in {item.value for item in LapExclusionReason}
    assert "invalid_duration" not in {item.value for item in LapExclusionReason}
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


def pace_estimate(value: float = 78.2, **updates) -> PaceEstimate:
    values = dict(
        value=78.2,
        competitor_id=COMPETITOR,
        as_of=NOW,
        sample_count=8,
        evidence_window=evidence_window(),
        model_version=CONFIG.version(),
    )
    values.update(updates)
    values["value"] = value
    return PaceEstimate(**values)


def test_pace_estimate_is_positive_representative_clean_lap_time_only():
    absolute = pace_estimate()
    assert absolute.unit == "s/lap"
    for value in (0.0, -0.18):
        with pytest.raises(ValidationError):
            pace_estimate(value)


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
    assert DegradationEstimate(**(estimate.model_dump() | {"value": -0.041})).value < 0
    for minimum in (16, 17):
        with pytest.raises(ValidationError):
            DegradationEstimate(**(estimate.model_dump() | {"minimum_tyre_age_laps": minimum}))


def test_observation_and_nested_provenance_cannot_postdate_lap_but_retrieval_may():
    completed = NOW - timedelta(minutes=2)
    later = completed + timedelta(seconds=1)
    retrieved_later = Provenance(source="archive", observed_at=completed, retrieved_at=NOW + timedelta(days=30))
    admitted = ModellingLapObservation(**(observation().model_dump() | {"provenance": (retrieved_later,)}))
    assert admitted.provenance[0].retrieved_at > NOW
    with pytest.raises(ValidationError):
        ModellingLapObservation(**(observation().model_dump() | {"provenance": (Provenance(source="laps", observed_at=later),)}))
    nested = (
        {"gap_evidence": GapEvidence(observed_at=completed, provenance=(Provenance(source="intervals", observed_at=later),))},
        {"track_status": TrackStatusEvidence(observed_at=completed, status=TrackStatus.GREEN, provenance=(Provenance(source="control", observed_at=later),))},
        {"weather": WeatherState(observed_at=completed, provenance=(Provenance(source="weather", observed_at=later),))},
    )
    for update in nested:
        with pytest.raises(ValidationError):
            ModellingLapObservation(**(observation().model_dump() | update))


def test_context_and_estimate_provenance_cannot_postdate_cutoff():
    future = Provenance(source="future", observed_at=NOW + timedelta(seconds=1))
    with pytest.raises(ValidationError):
        PaceEstimationContext(race_state=race_state(), as_of=NOW, provenance=(future,))
    with pytest.raises(ValidationError):
        pace_estimate(provenance=(future,))
    degradation = dict(
        value=0.041, competitor_id=COMPETITOR, as_of=NOW, compound=TyreCompound.MEDIUM,
        minimum_tyre_age_laps=5, maximum_tyre_age_laps=16, sample_count=8,
        evidence_window=evidence_window(), model_version=CONFIG.version(), provenance=(future,),
    )
    with pytest.raises(ValidationError):
        TyreDegradationEstimate(**degradation)


def test_new_modelling_timestamps_normalize_offsets_to_utc_and_reject_naive_values():
    offset = timezone(timedelta(hours=10))
    local_cutoff = NOW.astimezone(offset)
    local_completed = (NOW - timedelta(minutes=2)).astimezone(offset)
    window = EvidenceWindow(
        started_at=(NOW - timedelta(minutes=20)).astimezone(offset), ended_at=local_completed,
        first_lap=10, last_lap=20,
    )
    lap = observation(completed_at=local_completed)
    gap = GapEvidence(observed_at=local_completed)
    track = TrackStatusEvidence(observed_at=local_completed, status=TrackStatus.GREEN)
    context = PaceEstimationContext(race_state=race_state(), as_of=local_cutoff, observations=(lap,))
    diagnostics = FitDiagnostics(
        competitor_id=COMPETITOR, as_of=local_cutoff, candidate_laps=1,
        included_laps=1, excluded_laps=0, model_version=CONFIG.version(),
    )
    estimate = pace_estimate(as_of=local_cutoff, evidence_window=window)
    degradation = TyreDegradationEstimate(
        value=-0.01, competitor_id=COMPETITOR, as_of=local_cutoff, compound=TyreCompound.MEDIUM,
        minimum_tyre_age_laps=5, maximum_tyre_age_laps=6, sample_count=2,
        evidence_window=window, model_version=CONFIG.version(),
    )
    assert all(value.utcoffset() == timedelta(0) for value in (
        window.started_at, window.ended_at, lap.completed_at, gap.observed_at, track.observed_at,
        context.as_of, diagnostics.as_of, estimate.as_of, degradation.as_of,
    ))
    with pytest.raises(ValidationError):
        observation(completed_at=NOW.replace(tzinfo=None))
    with pytest.raises(ValidationError):
        EvidenceWindow(started_at=NOW.replace(tzinfo=None), ended_at=NOW, first_lap=1, last_lap=2)


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


def test_fit_diagnostics_bounds_source_observation_but_not_retrieval_time():
    observed = NOW - timedelta(seconds=1)
    retrieved = NOW + timedelta(days=30)
    valid = FitDiagnostics(
        competitor_id=COMPETITOR,
        as_of=NOW,
        candidate_laps=1,
        included_laps=1,
        excluded_laps=0,
        model_version=CONFIG.version(),
        provenance=(Provenance(source="archive", observed_at=observed, retrieved_at=retrieved),),
    )
    assert valid.provenance[0].observed_at <= valid.as_of
    assert valid.provenance[0].retrieved_at > valid.as_of
    with pytest.raises(ValidationError):
        FitDiagnostics(**(
            valid.model_dump()
            | {"provenance": (Provenance(source="future", observed_at=NOW + timedelta(seconds=1)),)}
        ))
