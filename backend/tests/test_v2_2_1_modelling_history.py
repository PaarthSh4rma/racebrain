from copy import deepcopy
from datetime import datetime, timezone
import random

import pytest

from app.adapters.openf1_v2.dto import IntervalDTO, LapDTO, PitDTO, PositionDTO, RaceControlDTO, StintDTO, WeatherDTO
from app.adapters.openf1_v2.mapper import OpenF1Dataset, ParsedRecords
from app.adapters.openf1_v2.modelling_history import build_pace_context
from app.application_v2.build_pace_context import build_historical_pace_context
from app.application_v2.reconstruct_race_state import HistoricalRaceStateRequest, _parse
from app.domain_v2.enums import (
    DataQualityLevel,
    LapAdmissionRejectionReason,
    LapExclusionReason,
    LapQualityWarning,
    TrackStatus,
    TyreCompound,
)
from app.domain_v2.provenance import DataQuality
from tests.fixtures.openf1_v2_fixtures import RecordingOpenF1Client, historical_payload


class CachingRecordingClient(RecordingOpenF1Client):
    def __init__(self, payload):
        super().__init__(payload)
        self.network_calls = []
        self.seen = set()

    def _take(self, name):
        self.calls.append(name)
        self.last_cache_hit = name in self.seen
        if not self.last_cache_hit:
            self.network_calls.append(name)
            self.seen.add(name)
        return deepcopy(self.payload[name])


def build(payload=None, lap=2):
    payload = payload or historical_payload()
    client = CachingRecordingClient(payload)
    result = build_historical_pace_context(
        HistoricalRaceStateRequest(openf1_session_key=999, focal_driver_number=16, decision_lap=lap),
        client,
    )
    return result, client


def observation(result, driver_number, lap_number):
    competitor = next(
        car.competitor_id
        for car in result.context.race_state.competitors
        if any(item.resource_type == "driver_number" and item.value == str(driver_number) for item in car.external_ids)
    )
    return next(item for item in result.context.observations if item.competitor_id == competitor and item.lap_number == lap_number)


def modelling_dataset(payload):
    empty = ParsedRecords(())
    return OpenF1Dataset(
        sessions=empty, meetings=empty, drivers=empty,
        laps=_parse(payload["laps"], LapDTO),
        stints=_parse(payload["stints"], StintDTO),
        intervals=_parse(payload["intervals"], IntervalDTO),
        positions=_parse(payload["positions"], PositionDTO),
        pits=_parse(payload["pits"], PitDTO),
        weather=_parse(payload["weather"], WeatherDTO),
        race_control=_parse(payload["race_control"], RaceControlDTO),
    )


def test_full_field_builder_uses_canonical_cutoff_identity_and_session_scoped_cache():
    result, client = build()
    assert result.context.as_of == result.context.race_state.observation_cutoff
    assert len(result.context.observations) == 3
    assert {item.competitor_id for item in result.context.observations} <= {
        car.competitor_id for car in result.context.race_state.competitors
    }
    assert client.network_calls == [
        "sessions", "meetings", "drivers", "laps", "stints", "intervals",
        "positions", "pits", "weather", "race_control",
    ]
    assert all(result.modelling_feed_cache_hits.values())
    assert observation(result, 16, 2).track_status.status is TrackStatus.GREEN


def test_admission_rejections_bounded_scope_and_conflicting_laps_are_distinct():
    payload = historical_payload()
    payload["laps"].extend([
        {"session_key": 999, "driver_number": 4, "lap_number": 4, "date_start": None, "lap_duration": 60},
        {"session_key": 999, "driver_number": 4, "lap_number": 5, "date_start": "2024-05-26T13:00:00Z", "lap_duration": 0},
        {"session_key": 999, "driver_number": 4, "lap_number": 0, "date_start": "2024-05-26T13:00:00Z", "lap_duration": 60},
        {"session_key": 999, "driver_number": 4, "lap_number": 1, "date_start": "2024-05-26T13:00:03Z", "lap_duration": 61},
        {"session_key": 999, "driver_number": 99, "lap_number": 1, "date_start": "2024-05-26T13:00:00Z", "lap_duration": 60},
        {"session_key": 123, "driver_number": 4, "lap_number": 6, "date_start": "2024-05-26T13:00:00Z", "lap_duration": 60},
        {"session_key": 999, "driver_number": 4, "lap_number": 50, "date_start": "2024-05-26T14:00:00Z", "lap_duration": 60},
    ])
    result, _ = build(payload)
    rejected = result.diagnostics.admission_rejections
    assert rejected[LapAdmissionRejectionReason.MISSING_TIMING] >= 2
    assert rejected[LapAdmissionRejectionReason.INVALID_DURATION] == 1
    assert rejected[LapAdmissionRejectionReason.INVALID_LAP_NUMBER] == 1
    assert rejected[LapAdmissionRejectionReason.CONFLICTING_TIMING_EVIDENCE] == 1
    assert result.diagnostics.conflicting_laps == 1
    assert result.diagnostics.unmapped_competitor_rows >= 1
    assert result.diagnostics.foreign_session_rows >= 1
    assert result.diagnostics.rows_bounded_out >= 1
    assert result.context.data_quality.warnings == tuple(sorted(set(result.context.data_quality.warnings)))
    assert "conflicting timed lap evidence was omitted" in result.context.data_quality.warnings
    assert set(result.context.race_state.data_quality.warnings) <= set(result.context.data_quality.warnings)
    with pytest.raises(StopIteration):
        observation(result, 4, 1)


@pytest.mark.parametrize("duration", [-1, float("nan"), float("inf"), float("-inf")])
def test_nonpositive_or_nonfinite_duration_is_rejected_without_timing_fallback(duration):
    payload = historical_payload()
    payload["laps"][2]["lap_duration"] = duration
    result, _ = build(payload)
    assert result.diagnostics.admission_rejections[LapAdmissionRejectionReason.INVALID_DURATION] == 1
    with pytest.raises(StopIteration):
        observation(result, 4, 1)


def test_exact_duplicate_lap_is_harmless_and_all_provider_ordering_is_irrelevant():
    payload = historical_payload()
    payload["laps"].append(deepcopy(payload["laps"][0]))
    first, _ = build(payload)
    shuffled = deepcopy(payload)
    rng = random.Random(8675309)
    for name in ("laps", "stints", "weather", "race_control", "intervals", "positions", "pits"):
        rng.shuffle(shuffled[name])
    second, _ = build(shuffled)
    assert first.context == second.context
    assert first.diagnostics == second.diagnostics
    assert first.diagnostics.exact_duplicate_laps == 1


def test_tyre_annotation_uses_bounded_start_formula_and_ignores_lap_end_and_future_start():
    payload = historical_payload()
    payload["stints"][0]["lap_end"] = 1
    payload["stints"].append({
        "session_key": 999, "driver_number": 16, "stint_number": 2, "lap_start": 3,
        "lap_end": 78, "compound": "SOFT", "tyre_age_at_start": 10,
    })
    result, _ = build(payload)
    lap = observation(result, 16, 2)
    assert (lap.compound, lap.tyre_age_laps, lap.stint_number) == (TyreCompound.MEDIUM, 2, 1)
    assert result.diagnostics.future_stint_starts == 1
    stint_source = next(item for item in lap.provenance if "stint" in " ".join(item.transformations))
    assert stint_source.observed_at is None
    assert "lap_end ignored" in " ".join(stint_source.transformations)


def test_unknown_missing_negative_duplicate_and_conflicting_stint_evidence_are_conservative():
    unknown = historical_payload()
    unknown["stints"][0]["compound"] = "EXPERIMENTAL"
    assert observation(build(unknown)[0], 16, 2).compound is TyreCompound.UNKNOWN
    missing = historical_payload()
    missing["stints"][0]["compound"] = None
    assert observation(build(missing)[0], 16, 2).compound is None
    negative = historical_payload()
    negative["stints"][0]["tyre_age_at_start"] = -1
    assert observation(build(negative)[0], 16, 2).tyre_age_laps is None
    duplicate = historical_payload()
    duplicate["stints"].append(deepcopy(duplicate["stints"][0]))
    assert observation(build(duplicate)[0], 16, 2).compound is TyreCompound.MEDIUM
    conflict = historical_payload()
    row = deepcopy(conflict["stints"][0])
    row["compound"] = "SOFT"
    conflict["stints"].append(row)
    result, _ = build(conflict)
    assert observation(result, 16, 2).compound is None
    assert result.diagnostics.ambiguous_stint_annotations == 2


@pytest.mark.parametrize("message,reason,status", [
    ("SAFETY CAR DEPLOYED", LapExclusionReason.SAFETY_CAR, TrackStatus.SAFETY_CAR),
    ("VIRTUAL SAFETY CAR DEPLOYED", LapExclusionReason.VSC, TrackStatus.VSC),
])
def test_global_caution_during_lap_is_aligned_and_excluded(message, reason, status):
    payload = historical_payload()
    payload["race_control"].append({
        "session_key": 999, "date": "2024-05-26T13:01:30Z", "scope": "Track",
        "category": "SafetyCar", "message": message,
    })
    lap = observation(build(payload)[0], 16, 2)
    assert lap.track_status.status is status
    assert reason in lap.hard_exclusions


def test_yellow_at_start_then_green_still_excludes_lap_window():
    payload = historical_payload()
    payload["race_control"].extend([
        {"session_key": 999, "date": "2024-05-26T13:00:50Z", "scope": "Track", "flag": "YELLOW", "message": "YELLOW FLAG"},
        {"session_key": 999, "date": "2024-05-26T13:01:30Z", "scope": "Track", "message": "TRACK GREEN"},
    ])
    lap = observation(build(payload)[0], 16, 2)
    assert lap.track_status.status is TrackStatus.GREEN
    assert LapExclusionReason.GLOBAL_YELLOW in lap.hard_exclusions


@pytest.mark.parametrize("deployment,ending,reason,status", [
    ("SAFETY CAR DEPLOYED", "SAFETY CAR IN THIS LAP", LapExclusionReason.SAFETY_CAR, TrackStatus.SAFETY_CAR),
    ("VIRTUAL SAFETY CAR DEPLOYED", "VSC ENDING", LapExclusionReason.VSC, TrackStatus.VSC),
])
def test_control_ending_messages_do_not_establish_green(deployment, ending, reason, status):
    payload = historical_payload()
    payload["race_control"].extend([
        {"session_key": 999, "date": "2024-05-26T13:00:50Z", "scope": "Track", "category": "SafetyCar", "message": deployment},
        {"session_key": 999, "date": "2024-05-26T13:01:30Z", "scope": "Track", "category": "SafetyCar", "message": ending},
    ])
    lap = observation(build(payload)[0], 16, 2)
    assert lap.track_status.status is status
    assert reason in lap.hard_exclusions


def test_control_non_transitions_local_flags_pit_exit_and_same_time_precedence():
    payload = historical_payload()
    payload["race_control"].extend([
        {"session_key": 999, "date": "2024-05-26T13:01:20Z", "scope": "Track", "category": "SafetyCar", "message": "SAFETY CAR DEPLOYED"},
        {"session_key": 999, "date": "2024-05-26T13:01:25Z", "scope": "Track", "category": "SafetyCar", "message": "SAFETY CAR IN THIS LAP"},
        {"session_key": 999, "date": "2024-05-26T13:01:30Z", "scope": "Sector", "flag": "YELLOW"},
        {"session_key": 999, "date": "2024-05-26T13:01:35Z", "scope": "Track", "flag": "GREEN", "message": "GREEN LIGHT - PIT EXIT OPEN"},
        {"session_key": 999, "date": "2024-05-26T13:01:40Z", "scope": "Track", "message": "TRACK GREEN"},
        {"session_key": 999, "date": "2024-05-26T13:01:50Z", "scope": "Track", "message": "TRACK GREEN"},
        {"session_key": 999, "date": "2024-05-26T13:01:50Z", "scope": "Track", "message": "VSC DEPLOYED"},
        {"session_key": 999, "date": "2024-05-26T13:01:50Z", "scope": "Track", "message": "SAFETY CAR DEPLOYED"},
        {"session_key": 999, "date": "2024-05-26T13:01:50Z", "scope": "Track", "flag": "RED", "message": "RED FLAG"},
    ])
    lap = observation(build(payload)[0], 16, 2)
    assert lap.track_status.status is TrackStatus.RED
    assert LapExclusionReason.SAFETY_CAR in lap.hard_exclusions
    assert LapExclusionReason.RED_FLAG in lap.hard_exclusions


def test_weather_is_latest_before_each_lap_not_latest_at_cutoff_and_transition_is_categorical():
    payload = historical_payload()
    payload["weather"].insert(0, {
        "session_key": 999, "date": "2024-05-26T13:00:30Z", "air_temperature": 21,
        "humidity": 50, "rainfall": 0,
    })
    payload["weather"].insert(1, {
        "session_key": 999, "date": "2024-05-26T13:01:30Z", "air_temperature": float("inf"),
        "humidity": 50, "rainfall": 1,
    })
    payload["weather"].insert(2, {
        "session_key": 999, "date": "2024-05-26T13:01:40Z", "air_temperature": 20,
        "humidity": 70, "rainfall": 1,
    })
    result, _ = build(payload)
    first, second = observation(result, 16, 1), observation(result, 16, 2)
    assert first.weather.observed_at == datetime(2024, 5, 26, 13, 0, 30, tzinfo=timezone.utc)
    assert second.weather.observed_at == datetime(2024, 5, 26, 13, 1, 40, tzinfo=timezone.utc)
    assert LapQualityWarning.WEATHER_TRANSITION in second.quality_warnings


@pytest.mark.parametrize("newest,expected_ahead,expected_leader", [
    ({"interval": 2.5, "gap_to_leader": "bad"}, (2.5, None), None),
    ({"interval": "bad", "gap_to_leader": "+1 LAP"}, None, (None, 1)),
    ({"interval": "bad", "gap_to_leader": "bad"}, (1.5, None), (8.0, None)),
])
def test_nonleader_gap_dimensions_are_independent_and_fallback_only_when_both_unusable(
    newest, expected_ahead, expected_leader,
):
    payload = historical_payload()
    payload["intervals"] = [row for row in payload["intervals"] if row["driver_number"] != 4]
    payload["intervals"].extend([
        {"session_key": 999, "driver_number": 4, "date": "2024-05-26T13:01:00Z", "interval": 1.5, "gap_to_leader": 8.0},
        {"session_key": 999, "driver_number": 4, "date": "2024-05-26T13:01:01Z", **newest},
    ])
    result, _ = build(payload)
    other = observation(result, 4, 1).gap_evidence
    actual_ahead = None if other.gap_ahead is None else (other.gap_ahead.seconds, other.gap_ahead.laps)
    actual_leader = None if other.gap_to_leader is None else (other.gap_to_leader.seconds, other.gap_to_leader.laps)
    assert actual_ahead == expected_ahead
    assert actual_leader == expected_leader
    reconstructed = result.context.race_state
    car = next(car for car in reconstructed.competitors if car.external_ids[0].value == "4")
    assert car.gap_ahead == other.gap_ahead
    assert car.gap_to_leader == other.gap_to_leader


def test_leader_interval_is_irrelevant_and_explicit_zero_to_leader_is_preserved():
    payload = historical_payload()
    payload["intervals"].append({
        "session_key": 999, "driver_number": 16, "date": "2024-05-26T13:01:59.5Z",
        "interval": "irrelevant", "gap_to_leader": 0.0,
    })
    result, _ = build(payload)
    leader = observation(result, 16, 2).gap_evidence
    assert leader.gap_ahead is None and leader.gap_to_leader.seconds == 0.0


def test_pit_out_and_exact_passage_are_factual_but_duplicates_future_and_adjacent_are_not():
    payload = historical_payload()
    payload["laps"][0]["is_pit_out_lap"] = True
    payload["pits"].append(deepcopy(payload["pits"][0]))
    payload["pits"].append({"session_key": 999, "driver_number": 16, "date": "2024-05-26T14:00:00Z", "lap_number": 2})
    result, _ = build(payload)
    first = observation(result, 16, 1)
    second = observation(result, 16, 2)
    other = observation(result, 4, 1)
    assert LapExclusionReason.PIT_OUT in first.hard_exclusions
    assert LapExclusionReason.PIT_LANE_AFFECTED not in second.hard_exclusions
    assert other.hard_exclusions.count(LapExclusionReason.PIT_LANE_AFFECTED) == 1
    assert result.diagnostics.pit_lane_affected_observations == 1
    assert "pit_stop_count" not in type(first).model_fields


def test_future_contamination_cannot_change_context_or_provenance():
    clean = historical_payload()
    dirty = deepcopy(clean)
    dirty["laps"].append({"session_key": 999, "driver_number": 4, "lap_number": 50, "date_start": "2024-05-26T14:00:00Z", "lap_duration": 60})
    dirty["stints"].append({"session_key": 999, "driver_number": 4, "lap_start": 50, "stint_number": 9, "compound": "WET", "tyre_age_at_start": 20})
    dirty["race_control"].extend([
        {"session_key": 999, "date": "2024-05-26T13:03:00Z", "scope": "Track", "message": "TRACK GREEN"},
        {"session_key": 999, "date": "2024-05-26T14:00:00Z", "scope": "Track", "flag": "RED", "message": "RED FLAG"},
    ])
    dirty["weather"].append({"session_key": 999, "date": "2024-05-26T14:00:00Z", "rainfall": 1})
    dirty["intervals"].append({"session_key": 999, "driver_number": 4, "date": "2024-05-26T14:00:00Z", "interval": 999})
    dirty["positions"].append({"session_key": 999, "driver_number": 4, "date": "2024-05-26T14:00:00Z", "position": 1})
    dirty["pits"].append({"session_key": 999, "driver_number": 4, "date": "2024-05-26T14:00:00Z", "lap_number": 50})
    assert build(clean)[0].context == build(dirty)[0].context


def test_cutoff_advance_adds_laps_and_preserves_historical_prefix():
    payload = historical_payload()
    payload["laps"].append({
        "session_key": 999, "driver_number": 16, "lap_number": 3,
        "date_start": "2024-05-26T13:02:00Z", "lap_duration": 60,
    })
    early, _ = build(payload, lap=2)
    late, _ = build(payload, lap=3)
    late_prefix = tuple(item for item in late.context.observations if item.completed_at <= early.context.as_of)
    assert late_prefix == early.context.observations
    assert len(late.context.observations) > len(early.context.observations)
    assert early.context.as_of == datetime(2024, 5, 26, 13, 2, tzinfo=timezone.utc)


def test_quality_and_provenance_are_inspectable_without_fake_completeness():
    result, _ = build()
    assert all(item.data_quality.level is DataQualityLevel.DEGRADED for item in result.context.observations)
    assert all(item.data_quality.completeness is None for item in result.context.observations)
    assert all(
        source.observed_at is None or source.observed_at <= item.completed_at
        for item in result.context.observations
        for source in item.provenance
    )
    assert result.context.provenance[0].observed_at <= result.context.as_of


def test_good_race_state_is_degraded_by_builder_wide_completion_assumption_without_mutation():
    payload = historical_payload()
    reconstructed, _ = build(payload)
    original_state = reconstructed.context.race_state
    good_state = original_state.model_copy(update={
        "data_quality": DataQuality(
            level=DataQualityLevel.GOOD,
            warnings=("inherited warning",),
            missing_fields=("inherited field",),
        ),
    })
    context, _ = build_pace_context(good_state, modelling_dataset(payload), 999)
    assert context.data_quality.level is DataQualityLevel.DEGRADED
    assert context.data_quality.completeness is None
    assert context.data_quality.missing_fields == ("inherited field",)
    assert set(context.data_quality.warnings) >= {
        "inherited warning",
        "OpenF1 lap completion is approximated from date_start + lap_duration",
    }
    assert good_state.data_quality.level is DataQualityLevel.GOOD
    assert all(item.data_quality.level is DataQualityLevel.DEGRADED for item in context.observations)
