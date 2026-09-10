from copy import deepcopy
from datetime import datetime, timezone

import pytest

from app.adapters.openf1_v2.identity import competitor_id, event_id, session_id
from app.adapters.openf1_v2.mapper import ReconstructionFailure
from app.adapters.openf1_v2.parsing import parse_gap, utc_datetime
from app.application_v2.reconstruct_race_state import HistoricalRaceStateRequest, reconstruct_historical_race_state
from app.domain_v2.enums import DataQualityLevel, TrackStatus
from tests.fixtures.openf1_v2_fixtures import RecordingOpenF1Client, historical_payload


def build(payload=None, *, session_key=999, lap=2):
    payload = payload or historical_payload(session_key)
    client = RecordingOpenF1Client(payload)
    result = reconstruct_historical_race_state(HistoricalRaceStateRequest(openf1_session_key=session_key, focal_driver_number=16, decision_lap=lap), client)
    return result, client


def by_number(state, number):
    return next(car for car in state.competitors if car.external_ids[0].value == str(number))


def test_full_field_cutoff_and_mapping():
    result, client = build()
    state = result.race_state
    assert state.observation_cutoff == datetime(2024, 5, 26, 13, 2, tzinfo=timezone.utc)
    assert len(state.competitors) == 2
    assert [by_number(state, n).current_lap for n in (16, 4)] == [2, 1]
    assert by_number(state, 16).position == 1
    assert by_number(state, 16).gap_ahead is None
    assert by_number(state, 16).gap_to_leader.seconds == 0.0
    assert "interval" not in by_number(state, 16).data_quality.missing_fields
    assert by_number(state, 4).gap_ahead.seconds == 1.25
    assert by_number(state, 4).gap_to_leader.laps == 1
    assert by_number(state, 4).gap_behind is None
    assert by_number(state, 4).pit_stop_count is None
    assert by_number(state, 4).in_pit is None
    assert by_number(state, 16).tyre.age_laps == 2
    assert by_number(state, 16).tyre.tyre_set_id is None
    assert by_number(state, 16).driver_id is None
    assert state.weather.humidity_fraction == 0.6
    assert state.weather.wind_speed_mps == 2.5
    assert state.track_status.status is TrackStatus.GREEN
    assert state.data_quality.level is DataQualityLevel.DEGRADED
    assert result.diagnostics.excluded_competitors == 1
    assert result.diagnostics.bounded_pit_lane_passages == 1
    assert client.calls == ["sessions", "meetings", "drivers", "laps", "stints", "intervals", "positions", "pits", "weather", "race_control"]


def test_future_records_cannot_change_canonical_state():
    a = historical_payload()
    b = deepcopy(a)
    for payload, position, compound, flag in ((a, 20, "SOFT", "RED"), (b, 1, "WET", "YELLOW")):
        payload["laps"].append({"driver_number": 4, "lap_number": 50, "date_start": "2024-05-26T14:00:00Z", "lap_duration": 40})
        payload["positions"].append({"driver_number": 4, "date": "2024-05-26T14:01:00Z", "position": position})
        payload["intervals"].append({"driver_number": 4, "date": "2024-05-26T14:01:00Z", "interval": "+9 LAPS", "gap_to_leader": 999})
        payload["stints"].append({"driver_number": 4, "stint_number": 9, "lap_start": 50, "lap_end": 51, "compound": compound, "tyre_age_at_start": 30})
        payload["pits"].append({"driver_number": 4, "date": "2024-05-26T14:01:00Z", "lap_number": 50})
        payload["weather"].append({"date": "2024-05-26T14:01:00Z", "humidity": 1, "rainfall": 1})
        payload["race_control"].append({"date": "2024-05-26T14:01:00Z", "scope": "Track", "flag": flag, "message": f"{flag} FLAG"})
    assert build(a)[0].race_state == build(b)[0].race_state


def test_later_cutoff_advances_state():
    payload = historical_payload()
    payload["laps"].append({"driver_number": 16, "lap_number": 3, "date_start": "2024-05-26T13:02:00Z", "lap_duration": 60})
    assert by_number(build(payload, lap=3)[0].race_state, 16).current_lap == 3


@pytest.mark.parametrize("value,seconds,laps", [("+1 LAP", None, 1), ("+2 LAPS", None, 2), ("1.75", 1.75, None), (2, 2.0, None)])
def test_gap_parsing(value, seconds, laps):
    assert parse_gap(value).seconds == seconds
    assert parse_gap(value).laps == laps


def test_missing_interval_and_position_degrade_car():
    payload = historical_payload()
    payload["intervals"] = []
    payload["positions"] = []
    car = by_number(build(payload)[0].race_state, 16)
    assert car.data_quality.level is DataQualityLevel.DEGRADED
    assert set(car.data_quality.missing_fields) >= {"interval", "position"}


def test_duplicates_and_order_are_deterministic():
    payload = historical_payload()
    payload["laps"].append(deepcopy(payload["laps"][0]))
    first = build(payload)[0]
    payload["laps"].reverse()
    payload["drivers"].reverse()
    second = build(payload)[0]
    assert first.race_state == second.race_state
    assert first.diagnostics.duplicate_records == second.diagnostics.duplicate_records == 1


def test_future_stint_endpoint_and_pit_are_not_used():
    payload = historical_payload()
    payload["stints"][0]["lap_end"] = 2
    original = build(payload)[0].race_state
    payload["stints"][0]["lap_end"] = 78
    payload["pits"].append({"driver_number": 16, "date": "2024-05-26T13:02:01Z", "lap_number": 2})
    changed = build(payload)[0].race_state
    assert by_number(original, 16).tyre == by_number(changed, 16).tyre
    assert by_number(changed, 16).pit_stop_count is None


@pytest.mark.parametrize("event,expected", [
    ({"date": "2024-05-26T13:01:50Z", "category": "SafetyCar", "scope": "Track", "message": "SAFETY CAR DEPLOYED"}, TrackStatus.SAFETY_CAR),
    ({"date": "2024-05-26T13:01:50Z", "scope": "Track", "message": "VIRTUAL SAFETY CAR DEPLOYED"}, TrackStatus.VSC),
    ({"date": "2024-05-26T13:01:50Z", "scope": "Track", "flag": "RED", "message": "RED FLAG"}, TrackStatus.RED),
    ({"date": "2024-05-26T13:01:50Z", "category": "SessionStatus", "message": "SESSION STARTED"}, TrackStatus.GREEN),
])
def test_track_status_explicit_transitions(event, expected):
    payload = historical_payload()
    payload["race_control"].append(event)
    assert build(payload)[0].race_state.track_status.status is expected


def test_bad_weather_humidity_is_ignored():
    payload = historical_payload()
    payload["weather"][0]["humidity"] = 101
    result = build(payload)[0]
    assert result.race_state.weather is None
    assert "weather" in result.race_state.data_quality.missing_fields


def test_cutoff_failure_is_typed_and_no_lap_number_fallback():
    payload = historical_payload()
    payload["laps"][1]["date_start"] = "not-a-date"
    with pytest.raises(ReconstructionFailure):
        build(payload)


def test_canonical_identity_ignores_provider_keys_and_order():
    first = build(historical_payload(999), session_key=999)[0].race_state
    changed_keys = historical_payload(1234)
    changed_keys["sessions"][0]["meeting_key"] = 4321
    changed_keys["meetings"][0]["meeting_key"] = 4321
    changed_keys["sessions"].reverse()
    changed_keys["meetings"].reverse()
    second = build(changed_keys, session_key=1234)[0].race_state
    assert first.session.session_id == second.session.session_id
    assert [car.competitor_id for car in first.competitors] == [car.competitor_id for car in second.competitors]
    eid = event_id(2024, "Monaco Grand Prix", "Monaco", "Monaco", "Monte Carlo")
    sid = session_id(eid, "Race", "Race")
    assert competitor_id(sid, 16) == competitor_id(sid, 16)


def test_tolerant_timestamp_parser_rejects_naive_and_malformed():
    assert utc_datetime("2024-05-26T15:00:00+02:00") == datetime(2024, 5, 26, 13, tzinfo=timezone.utc)
    assert utc_datetime("2024-05-26T13:00:00") is None
    assert utc_datetime("bad") is None


def test_foreign_session_contamination_cannot_change_state():
    clean = historical_payload()
    dirty = deepcopy(clean)
    foreign = 123
    dirty["drivers"].append({"session_key": foreign, "driver_number": 99, "full_name": "Intruder"})
    dirty["laps"].append({"session_key": foreign, "driver_number": 16, "lap_number": 2, "date_start": "2024-05-26T12:00:00Z", "lap_duration": 1})
    dirty["stints"].append({"session_key": foreign, "driver_number": 16, "lap_start": 2, "stint_number": 9, "compound": "WET", "tyre_age_at_start": 50})
    dirty["intervals"].append({"session_key": foreign, "driver_number": 16, "date": "2024-05-26T13:01:59.9Z", "interval": 0.001})
    dirty["positions"].append({"session_key": foreign, "driver_number": 16, "date": "2024-05-26T13:01:59.9Z", "position": 20})
    dirty["pits"].append({"session_key": foreign, "driver_number": 16, "date": "2024-05-26T13:01:59.9Z"})
    dirty["weather"].append({"session_key": foreign, "date": "2024-05-26T13:01:59.9Z", "humidity": 100, "rainfall": 1})
    dirty["race_control"].append({"session_key": foreign, "date": "2024-05-26T13:01:59.9Z", "scope": "Track", "flag": "RED", "message": "RED FLAG"})
    clean_state = build(clean)[0].race_state
    dirty_result = build(dirty)[0]
    assert dirty_result.race_state == clean_state
    assert dirty_result.diagnostics.foreign_session_records == 8


def test_foreign_focal_lap_cannot_establish_cutoff():
    payload = historical_payload()
    payload["laps"][1]["session_key"] = 123
    with pytest.raises(ReconstructionFailure):
        build(payload)


def test_focal_driver_entry_is_required():
    payload = historical_payload()
    payload["drivers"] = [row for row in payload["drivers"] if row["driver_number"] != 16]
    with pytest.raises(ReconstructionFailure, match="focal driver"):
        build(payload)


def test_focal_foreign_driver_entry_is_rejected():
    payload = historical_payload()
    next(row for row in payload["drivers"] if row["driver_number"] == 16)["session_key"] = 123
    with pytest.raises(ReconstructionFailure, match="focal driver"):
        build(payload)


def test_invalid_latest_position_falls_back_without_advancing_observed_at():
    payload = historical_payload()
    payload["positions"].append({"driver_number": 16, "date": "2024-05-26T13:01:59.9Z", "position": 0})
    car = by_number(build(payload)[0].race_state, 16)
    assert car.position == 1
    assert car.observed_at == datetime(2024, 5, 26, 13, 2, tzinfo=timezone.utc)


def test_invalid_latest_interval_falls_back_and_nonleader_null_is_missing():
    payload = historical_payload()
    payload["intervals"].append({"driver_number": 4, "date": "2024-05-26T13:01:59Z", "interval": "nonsense", "gap_to_leader": -1})
    assert by_number(build(payload)[0].race_state, 4).gap_ahead.seconds == 1.25
    payload["intervals"] = [{"driver_number": 4, "date": "2024-05-26T13:01:59Z", "interval": None, "gap_to_leader": "bad"}]
    car = by_number(build(payload)[0].race_state, 4)
    assert car.gap_ahead is None and "interval" in car.data_quality.missing_fields


def test_nonleader_zero_interval_is_preserved():
    payload = historical_payload()
    payload["intervals"][1]["interval"] = 0.0
    car = by_number(build(payload)[0].race_state, 4)
    assert car.position == 2
    assert car.gap_ahead.seconds == 0.0
    assert "interval" not in car.data_quality.missing_fields


@pytest.mark.parametrize("duration", [float("nan"), float("inf"), float("-inf"), 0, -1])
def test_nonfinite_or_nonpositive_focal_duration_cannot_establish_cutoff(duration):
    payload = historical_payload()
    payload["laps"][1]["lap_duration"] = duration
    with pytest.raises(ReconstructionFailure):
        build(payload)


def test_invalid_latest_weather_falls_back():
    payload = historical_payload()
    payload["weather"].insert(1, {"date": "2024-05-26T13:01:50Z", "air_temperature": float("inf"), "humidity": 50})
    assert build(payload)[0].race_state.weather.observed_at == datetime(2024, 5, 26, 13, 1, 30, tzinfo=timezone.utc)


def test_negative_tyre_age_is_not_clamped():
    payload = historical_payload()
    payload["stints"][0]["tyre_age_at_start"] = -10
    car = by_number(build(payload)[0].race_state, 16)
    assert car.tyre is None
    assert "tyre" in car.data_quality.missing_fields


def test_duplicate_pit_passage_does_not_change_canonical_state():
    clean = historical_payload()
    dirty = deepcopy(clean)
    dirty["pits"].append(deepcopy(dirty["pits"][0]))
    assert build(clean)[0].race_state == build(dirty)[0].race_state
    assert build(dirty)[0].diagnostics.bounded_pit_lane_passages == 1


def test_local_flags_and_pit_exit_green_do_not_change_global_state():
    payload = historical_payload()
    payload["race_control"].extend([
        {"date": "2024-05-26T13:01:40Z", "scope": "Sector", "flag": "YELLOW", "message": "YELLOW IN TRACK SECTOR 3"},
        {"date": "2024-05-26T13:01:45Z", "scope": "Driver", "flag": "YELLOW", "message": "YELLOW FOR CAR 4"},
        {"date": "2024-05-26T13:01:50Z", "scope": "Track", "flag": "GREEN", "message": "GREEN LIGHT - PIT EXIT OPEN"},
    ])
    assert build(payload)[0].race_state.track_status.status is TrackStatus.GREEN


def test_global_yellow_and_conservative_same_timestamp_precedence():
    payload = historical_payload()
    payload["race_control"].extend([
        {"date": "2024-05-26T13:01:50Z", "scope": "Track", "flag": "YELLOW", "message": "YELLOW FLAG"},
        {"date": "2024-05-26T13:01:50Z", "scope": "Track", "flag": "RED", "message": "RED FLAG"},
    ])
    assert build(payload)[0].race_state.track_status.status is TrackStatus.RED


@pytest.mark.parametrize("deployment,ending,expected", [
    ("VIRTUAL SAFETY CAR DEPLOYED", "VSC ENDING", TrackStatus.VSC),
    ("SAFETY CAR DEPLOYED", "SAFETY CAR IN THIS LAP", TrackStatus.SAFETY_CAR),
])
def test_control_ending_message_does_not_establish_green(deployment, ending, expected):
    payload = historical_payload()
    payload["race_control"].extend([
        {"date": "2024-05-26T13:01:40Z", "scope": "Track", "category": "SafetyCar", "message": deployment},
        {"date": "2024-05-26T13:01:50Z", "scope": "Track", "category": "SafetyCar", "message": ending},
    ])
    assert build(payload)[0].race_state.track_status.status is expected


def test_imola_and_monza_have_distinct_event_ids():
    imola = event_id(2024, "Emilia Romagna Grand Prix", "Italy", "Imola", "Imola")
    monza = event_id(2024, "Italian Grand Prix", "Italy", "Monza", "Monza")
    assert imola != monza


def test_future_malformed_evidence_cannot_change_state():
    clean = historical_payload()
    dirty = deepcopy(clean)
    dirty["laps"].append({"driver_number": 4, "lap_number": 99, "date_start": "2024-05-26T14:00:00Z", "lap_duration": float("nan")})
    dirty["positions"].append({"driver_number": 4, "date": "2024-05-26T14:00:00Z", "position": False})
    dirty["intervals"].append({"driver_number": 4, "date": "2024-05-26T14:00:00Z", "interval": "broken", "gap_to_leader": float("inf")})
    dirty["weather"].append({"date": "2024-05-26T14:00:00Z", "wind_speed": -1, "rainfall": "perhaps"})
    dirty["race_control"].append({"date": "2024-05-26T14:00:00Z", "scope": "Track", "flag": "RED", "message": "RED FLAG"})
    assert build(clean)[0].race_state == build(dirty)[0].race_state
