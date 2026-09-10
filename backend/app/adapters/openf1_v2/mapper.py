"""Cutoff-safe conversion from parsed OpenF1 records to canonical RaceState."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from math import isfinite
from typing import Generic, TypeVar

from app.domain_v2.enums import DataQualityLevel, TrackStatus, TyreCompound
from app.domain_v2.provenance import DataQuality, ExternalIdentifier, Provenance
from app.domain_v2.race_state import CarState, Event, LapObservation, RaceState, Session, TrackStatusState, WeatherState
from app.domain_v2.tyre import TyreSetState

from .dto import DriverDTO, IntervalDTO, LapDTO, MeetingDTO, PitDTO, PositionDTO, RaceControlDTO, SessionDTO, StintDTO, WeatherDTO
from .identity import competitor_id, event_id, session_id
from .parsing import parse_gap

T = TypeVar("T")


@dataclass(frozen=True)
class ParsedRecords(Generic[T]):
    records: tuple[T, ...]
    malformed: int = 0


@dataclass(frozen=True)
class OpenF1Dataset:
    sessions: ParsedRecords[SessionDTO]
    meetings: ParsedRecords[MeetingDTO]
    drivers: ParsedRecords[DriverDTO]
    laps: ParsedRecords[LapDTO]
    stints: ParsedRecords[StintDTO]
    intervals: ParsedRecords[IntervalDTO]
    positions: ParsedRecords[PositionDTO]
    pits: ParsedRecords[PitDTO]
    weather: ParsedRecords[WeatherDTO]
    race_control: ParsedRecords[RaceControlDTO]


@dataclass
class ReconstructionDiagnostics:
    malformed_records: int = 0
    future_records: int = 0
    untimed_records: int = 0
    duplicate_records: int = 0
    excluded_competitors: int = 0
    foreign_session_records: int = 0
    bounded_pit_lane_passages: int = 0
    included_records: dict[str, int] = field(default_factory=dict)
    cache_hits: dict[str, bool] = field(default_factory=dict)


class ReconstructionFailure(ValueError):
    """A canonical state cannot be established from the supplied evidence."""


def _external(resource: str, value: object) -> ExternalIdentifier:
    return ExternalIdentifier(provider="OpenF1", resource_type=resource, value=str(value))


def _source(resource: str, observed_at: datetime | None, session_key: int, *transforms: str) -> Provenance:
    return Provenance(
        source="OpenF1",
        source_version="v1",
        observed_at=observed_at,
        external_ids=(_external("session", session_key),),
        transformations=tuple(transforms),
    )


def _completed(lap: LapDTO) -> datetime | None:
    if lap.date_start is None or lap.lap_duration is None or not isfinite(lap.lap_duration) or lap.lap_duration <= 0:
        return None
    try:
        return lap.date_start + timedelta(seconds=lap.lap_duration)
    except OverflowError:
        return None


def decision_cutoff(laps: tuple[LapDTO, ...], driver_number: int, decision_lap: int) -> datetime:
    matches = sorted(
        (end for lap in laps if lap.driver_number == driver_number and lap.lap_number == decision_lap and (end := _completed(lap)) is not None)
    )
    if not matches:
        raise ReconstructionFailure("No timed focal lap can establish the requested decision cutoff.")
    return matches[0]


def _stable_record_key(item) -> tuple:
    return tuple((name, repr(value)) for name, value in sorted(item.model_dump().items()))


def _latest_position(records, driver_number: int, cutoff: datetime, diagnostics: ReconstructionDiagnostics):
    valid = []
    for item in records:
        if item.driver_number != driver_number:
            continue
        if item.date is None:
            diagnostics.untimed_records += 1
        elif item.date > cutoff:
            diagnostics.future_records += 1
        elif isinstance(item.position, bool) or not isinstance(item.position, int) or item.position <= 0:
            diagnostics.malformed_records += 1
        else:
            valid.append((item.date, _stable_record_key(item), item))
    if not valid:
        return None
    diagnostics.included_records["position"] = diagnostics.included_records.get("position", 0) + 1
    return max(valid, key=lambda value: (value[0], value[1]))[2]


def _latest_interval(records, driver_number: int, cutoff: datetime, is_leader: bool, diagnostics: ReconstructionDiagnostics):
    valid = []
    for item in records:
        if item.driver_number != driver_number:
            continue
        if item.date is None:
            diagnostics.untimed_records += 1
            continue
        if item.date > cutoff:
            diagnostics.future_records += 1
            continue
        ahead, leader = parse_gap(item.interval), parse_gap(item.gap_to_leader)
        if ahead is None and leader is None and not is_leader:
            diagnostics.malformed_records += 1
            continue
        valid.append((item.date, _stable_record_key(item), item, ahead, leader))
    if not valid:
        return None
    diagnostics.included_records["intervals"] = diagnostics.included_records.get("intervals", 0) + 1
    return max(valid, key=lambda value: (value[0], value[1]))


def _quality(missing: list[str], warnings: list[str], insufficient: bool = False) -> DataQuality:
    level = DataQualityLevel.INSUFFICIENT if insufficient else (DataQualityLevel.DEGRADED if missing or warnings else DataQualityLevel.GOOD)
    return DataQuality(level=level, completeness=None, warnings=tuple(sorted(set(warnings))), missing_fields=tuple(sorted(set(missing))))


def _tyre(stints: tuple[StintDTO, ...], number: int, lap_number: int | None, session_key: int):
    if lap_number is None:
        return None
    applicable = sorted(
        (s for s in stints if s.driver_number == number and s.lap_start is not None and 1 <= s.lap_start <= lap_number),
        key=lambda s: (s.lap_start or 0, s.stint_number or 0, _stable_record_key(s)), reverse=True,
    )
    for stint in applicable:
        if stint.tyre_age_at_start is None or stint.tyre_age_at_start < 0 or (stint.stint_number is not None and stint.stint_number < 1):
            continue
        age = stint.tyre_age_at_start + lap_number - stint.lap_start + 1
        if age < 0:
            continue
        compounds = {item.value.upper(): item for item in TyreCompound}
        compound = compounds.get((stint.compound or "").upper(), TyreCompound.UNKNOWN)
        return TyreSetState(
            compound=compound, age_laps=age, stint_number=stint.stint_number,
            provenance=(_source("stints", None, session_key, "tyre age reconstructed from bounded stint start; lap_end ignored"),),
        )
    return None


def _weather(records: tuple[WeatherDTO, ...], cutoff: datetime, session_key: int, diagnostics: ReconstructionDiagnostics):
    candidates = []
    for item in records:
        if item.date is None:
            diagnostics.untimed_records += 1
        elif item.date > cutoff:
            diagnostics.future_records += 1
        elif not _usable_weather(item):
            diagnostics.malformed_records += 1
        else:
            candidates.append((item.date, _stable_record_key(item), item))
    if not candidates:
        return None
    item = max(candidates, key=lambda value: (value[0], value[1]))[2]
    diagnostics.included_records["weather"] = 1
    return WeatherState(
        observed_at=item.date,
        air_temperature_c=item.air_temperature,
        track_temperature_c=item.track_temperature,
        humidity_fraction=item.humidity / 100 if item.humidity is not None else None,
        wind_speed_mps=item.wind_speed,
        rainfall_detected=bool(item.rainfall) if item.rainfall is not None else None,
        provenance=(_source("weather", item.date, session_key, "humidity percent converted to fraction"),),
    )


def _usable_weather(item: WeatherDTO) -> bool:
    bounded = ((item.air_temperature, -50, 80), (item.track_temperature, -50, 100))
    if any(value is not None and (not isfinite(value) or not low <= value <= high) for value, low, high in bounded):
        return False
    if item.humidity is not None and (not isfinite(item.humidity) or not 0 <= item.humidity <= 100):
        return False
    if item.wind_speed is not None and (not isfinite(item.wind_speed) or item.wind_speed < 0):
        return False
    return item.rainfall is None or item.rainfall is True or item.rainfall is False or type(item.rainfall) is int and item.rainfall in (0, 1)


def _status(records: tuple[RaceControlDTO, ...], cutoff: datetime, session_key: int, diagnostics: ReconstructionDiagnostics):
    states = []
    precedence = {TrackStatus.GREEN: 1, TrackStatus.YELLOW: 2, TrackStatus.VSC: 3, TrackStatus.SAFETY_CAR: 4, TrackStatus.RED: 5}
    for item in records:
        if item.date is None:
            diagnostics.untimed_records += 1
            continue
        if item.date > cutoff:
            diagnostics.future_records += 1
            continue
        flag = (item.flag or "").upper()
        message = (item.message or "").upper()
        category = (item.category or "").upper()
        scope = (item.scope or "").upper()
        status = None
        global_track = scope == "TRACK"
        global_event = scope in {"", "TRACK"}
        if (global_track and (flag == "RED" or message == "RED FLAG")) or (global_event and category == "SESSIONSTATUS" and message in {"SESSION ABORTED", "SESSION SUSPENDED"}):
            status = TrackStatus.RED
        elif global_event and (global_track or category == "SAFETYCAR") and message in {"VIRTUAL SAFETY CAR DEPLOYED", "VSC DEPLOYED"}:
            status = TrackStatus.VSC
        elif global_event and (global_track or category == "SAFETYCAR") and message == "SAFETY CAR DEPLOYED":
            status = TrackStatus.SAFETY_CAR
        elif global_track and (flag in {"YELLOW", "DOUBLE YELLOW"} or message in {"YELLOW FLAG", "DOUBLE YELLOW"}):
            status = TrackStatus.YELLOW
        elif (global_event and category == "SESSIONSTATUS" and message == "SESSION STARTED") or global_track and message in {"GREEN FLAG", "TRACK GREEN"}:
            status = TrackStatus.GREEN
        if status is not None:
            states.append((item.date, precedence[status], status))
    if not states:
        return None
    observed_at, _, status = max(states, key=lambda value: (value[0], value[1]))
    diagnostics.included_records["race_control"] = 1
    return TrackStatusState(status=status, observed_at=observed_at, provenance=(_source("race_control", observed_at, session_key, "race-control event reduced by explicit flag/message rules"),))


def reconstruct(dataset: OpenF1Dataset, session_key: int, focal_driver_number: int, decision_lap: int, foreign_records: int = 0):
    diagnostics = ReconstructionDiagnostics(malformed_records=sum(part.malformed for part in dataset.__dict__.values()), foreign_session_records=foreign_records)
    session_candidates = sorted((s for s in dataset.sessions.records if s.session_key == session_key), key=_stable_record_key)
    if not session_candidates:
        raise ReconstructionFailure("OpenF1 session metadata is missing or unusable.")
    meta = session_candidates[0]
    meetings = list({ _stable_record_key(m): m for m in dataset.meetings.records if m.meeting_key == meta.meeting_key }.values())
    if len(meetings) != 1:
        raise ReconstructionFailure("Exactly one matching OpenF1 meeting is required.")
    meeting = meetings[0]
    if meeting.year is None or not all((meeting.meeting_name, meeting.country_name, meeting.location, meeting.circuit_short_name)) or not (meta.session_name or meta.session_type):
        raise ReconstructionFailure("Session metadata cannot establish canonical identity.")
    cutoff = decision_cutoff(dataset.laps.records, focal_driver_number, decision_lap)
    eid = event_id(meeting.year, meeting.meeting_name, meeting.country_name, meeting.location, meeting.circuit_short_name)
    sid = session_id(eid, meta.session_type or meta.session_name or "", meta.session_name or meta.session_type or "")
    event = Event(event_id=eid, name=meeting.meeting_name, circuit_id=None, external_ids=(_external("meeting", meta.meeting_key),))
    session = Session(session_id=sid, event=event, name=meta.session_name or meta.session_type or "Race", external_ids=(_external("session", session_key),))

    laps_by_driver = defaultdict(list)
    for index, lap in enumerate(dataset.laps.records):
        if lap.driver_number is None:
            continue
        completed = _completed(lap)
        if completed is None:
            diagnostics.untimed_records += 1
        elif completed > cutoff:
            diagnostics.future_records += 1
        elif lap.lap_number is None or lap.lap_number < 1:
            diagnostics.malformed_records += 1
        else:
            laps_by_driver[lap.driver_number].append((lap.lap_number, completed, index, lap))

    cars = []
    field_missing = []
    field_warnings = ["OpenF1 lap date_start is approximate; cutoff is derived from date_start + lap_duration"]
    seen_numbers = set()
    focal_seen = False
    for driver in sorted(dataset.drivers.records, key=_stable_record_key):
        number = driver.driver_number
        if number is None or number in seen_numbers or (driver.session_key is not None and driver.session_key != session_key):
            diagnostics.duplicate_records += number in seen_numbers
            continue
        seen_numbers.add(number)
        focal_seen = focal_seen or number == focal_driver_number
        deduped = {}
        for lap_no, completed, index, lap in laps_by_driver[number]:
            old = deduped.get(lap_no)
            if old is not None:
                diagnostics.duplicate_records += 1
            candidate = (completed, _stable_record_key(lap), lap)
            if old is None or candidate[:2] < old[:2]:
                deduped[lap_no] = candidate
        lap_rows = sorted(((no, *value) for no, value in deduped.items()), key=lambda value: (value[0], value[1]))
        position = _latest_position(dataset.positions.records, number, cutoff, diagnostics)
        interval_row = _latest_interval(dataset.intervals.records, number, cutoff, position is not None and position.position == 1, diagnostics)
        interval, gap_ahead, gap_leader = (interval_row[2], interval_row[3], interval_row[4]) if interval_row else (None, None, None)
        pits = {(p.date, _stable_record_key(p)): p for p in dataset.pits.records if p.driver_number == number and p.date is not None and p.date <= cutoff}
        diagnostics.duplicate_records += sum(1 for p in dataset.pits.records if p.driver_number == number and p.date is not None and p.date <= cutoff) - len(pits)
        pit_records = tuple(pits.values())
        diagnostics.bounded_pit_lane_passages += len(pit_records)
        diagnostics.future_records += sum(1 for p in dataset.pits.records if p.driver_number == number and p.date is not None and p.date > cutoff)
        diagnostics.untimed_records += sum(1 for p in dataset.pits.records if p.driver_number == number and p.date is None)
        timestamps = ([lap_rows[-1][1]] if lap_rows else []) + ([position.date] if position else []) + ([interval.date] if interval else []) + [p.date for p in pit_records]
        if not timestamps:
            diagnostics.excluded_competitors += 1
            field_missing.append(f"competitor[{number}].timestamped_state")
            continue
        current_lap = lap_rows[-1][0] if lap_rows else None
        tyre = _tyre(dataset.stints.records, number, current_lap, session_key)
        missing, warnings = [], []
        for absent, label in ((not lap_rows, "lap_timing"), (position is None, "position"), (interval is None, "interval"), (tyre is None, "tyre")):
            if absent:
                missing.append(label)
        lap_observations = tuple(LapObservation(lap_number=no, lap_time_s=lap.lap_duration, completed_at=completed, is_pit_out_lap=lap.is_pit_out_lap) for no, completed, _, lap in lap_rows[-10:])
        provenance = []
        if lap_rows:
            provenance.append(_source("laps", lap_rows[-1][1], session_key, "lap completion derived from date_start + lap_duration"))
        if position:
            provenance.append(_source("position", position.date, session_key, "latest record at or before cutoff"))
        if interval:
            provenance.append(_source("intervals", interval.date, session_key, "seconds or lapped interval parsed to canonical Gap"))
        if pit_records:
            provenance.append(_source("pit", max(p.date for p in pit_records), session_key, "timestamp-bounded pit-lane passage observed; stop semantics not inferred"))
        cars.append(CarState(
            competitor_id=competitor_id(sid, number), observed_at=max(timestamps), driver_id=None,
            driver_name=driver.full_name or " ".join(filter(None, (driver.first_name, driver.last_name))) or None,
            position=position.position if position else None,
            current_lap=current_lap, gap_ahead=gap_ahead,
            gap_behind=None, gap_to_leader=gap_leader,
            tyre=tyre, recent_laps=lap_observations, in_pit=None, pit_stop_count=None,
            data_quality=_quality(missing, warnings), provenance=tuple(provenance),
            external_ids=(_external("driver_number", number),),
        ))
    if not cars:
        raise ReconstructionFailure("No competitor has timestamped evidence at or before the cutoff.")
    if not focal_seen:
        raise ReconstructionFailure("The focal driver is missing from session driver entries.")
    if not any(car.external_ids[0].value == str(focal_driver_number) for car in cars):
        raise ReconstructionFailure("The focal competitor has no defensible timestamped state at the cutoff.")
    weather = _weather(dataset.weather.records, cutoff, session_key, diagnostics)
    status = _status(dataset.race_control.records, cutoff, session_key, diagnostics)
    if weather is None:
        field_missing.append("weather")
    if status is None:
        field_missing.append("track_status")
    if diagnostics.excluded_competitors:
        field_warnings.append("competitors without timestamped evidence were excluded")
    state = RaceState(
        session=session, observation_cutoff=cutoff, track_status=status, weather=weather,
        competitors=tuple(sorted(cars, key=lambda car: int(car.external_ids[0].value))),
        data_quality=_quality(field_missing, field_warnings),
        provenance=(_source("historical session datasets", cutoff, session_key, "full-field reconstruction bounded by focal completed-lap cutoff", "provider identifiers retained as metadata only"),),
    )
    return state, diagnostics
