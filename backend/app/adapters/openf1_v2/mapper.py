"""Cutoff-safe conversion from parsed OpenF1 records to canonical RaceState."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Generic, TypeVar

from app.domain_v2.enums import DataQualityLevel, TrackStatus, TyreCompound
from app.domain_v2.provenance import DataQuality, ExternalIdentifier, Provenance
from app.domain_v2.race_state import CarState, Event, LapObservation, RaceState, Session, TrackStatusState, WeatherState
from app.domain_v2.tyre import TyreSetState

from .dto import DriverDTO, IntervalDTO, LapDTO, PitDTO, PositionDTO, RaceControlDTO, SessionDTO, StintDTO, WeatherDTO
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
    if lap.date_start is None or lap.lap_duration is None or lap.lap_duration <= 0:
        return None
    return lap.date_start + timedelta(seconds=lap.lap_duration)


def decision_cutoff(laps: tuple[LapDTO, ...], driver_number: int, decision_lap: int) -> datetime:
    matches = sorted(
        (end for lap in laps if lap.driver_number == driver_number and lap.lap_number == decision_lap and (end := _completed(lap)) is not None)
    )
    if not matches:
        raise ReconstructionFailure("No timed focal lap can establish the requested decision cutoff.")
    return matches[0]


def _stable_record_key(item) -> tuple:
    return tuple((name, repr(value)) for name, value in sorted(item.model_dump().items()))


def _latest_dated(records, driver_number: int, cutoff: datetime, diagnostics: ReconstructionDiagnostics, dataset: str):
    valid = []
    for index, item in enumerate(records):
        if item.driver_number != driver_number:
            continue
        if item.date is None:
            diagnostics.untimed_records += 1
        elif item.date > cutoff:
            diagnostics.future_records += 1
        else:
            valid.append((item.date, _stable_record_key(item), item))
    if not valid:
        return None
    diagnostics.included_records[dataset] = diagnostics.included_records.get(dataset, 0) + 1
    return max(valid, key=lambda value: (value[0], value[1]))[2]


def _quality(missing: list[str], warnings: list[str], insufficient: bool = False) -> DataQuality:
    level = DataQualityLevel.INSUFFICIENT if insufficient else (DataQualityLevel.DEGRADED if missing or warnings else DataQualityLevel.GOOD)
    return DataQuality(level=level, completeness=None, warnings=tuple(sorted(set(warnings))), missing_fields=tuple(sorted(set(missing))))


def _tyre(stints: tuple[StintDTO, ...], number: int, lap_number: int | None, session_key: int):
    if lap_number is None:
        return None
    applicable = [s for s in stints if s.driver_number == number and s.lap_start is not None and s.lap_start <= lap_number]
    if not applicable:
        return None
    stint = max(applicable, key=lambda s: (s.lap_start or 0, s.stint_number or 0))
    if stint.tyre_age_at_start is None:
        return None
    age = stint.tyre_age_at_start + lap_number - (stint.lap_start or lap_number) + 1
    compounds = {item.value.upper(): item for item in TyreCompound}
    compound = compounds.get((stint.compound or "").upper(), TyreCompound.UNKNOWN)
    return TyreSetState(
        compound=compound,
        age_laps=max(0, age),
        stint_number=stint.stint_number,
        provenance=(_source("stints", None, session_key, "tyre age reconstructed from stint start and latest completed lap; lap_end ignored"),),
    )


def _weather(records: tuple[WeatherDTO, ...], cutoff: datetime, session_key: int, diagnostics: ReconstructionDiagnostics):
    candidates = []
    for index, item in enumerate(records):
        if item.date is None:
            diagnostics.untimed_records += 1
        elif item.date > cutoff:
            diagnostics.future_records += 1
        elif item.humidity is not None and not 0 <= item.humidity <= 100:
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


def _status(records: tuple[RaceControlDTO, ...], cutoff: datetime, session_key: int, diagnostics: ReconstructionDiagnostics):
    states = []
    for index, item in enumerate(records):
        if item.date is None:
            diagnostics.untimed_records += 1
            continue
        if item.date > cutoff:
            diagnostics.future_records += 1
            continue
        flag = (item.flag or "").upper()
        message = (item.message or "").upper()
        category = (item.category or "").upper()
        status = None
        if flag == "RED" or "RED FLAG" in message:
            status = TrackStatus.RED
        elif "VIRTUAL SAFETY CAR" in message or "VSC DEPLOYED" in message:
            status = TrackStatus.VSC
        elif category == "SAFETYCAR" and ("DEPLOYED" in message or "SAFETY CAR" in message and "ENDING" not in message):
            status = TrackStatus.SAFETY_CAR
        elif flag == "YELLOW" or "YELLOW FLAG" in message:
            status = TrackStatus.YELLOW
        elif (category == "SESSIONSTATUS" and message == "SESSION STARTED") or flag == "GREEN" or "GREEN FLAG" in message or "VSC ENDING" in message or "SAFETY CAR IN THIS LAP" in message:
            status = TrackStatus.GREEN
        if status is not None:
            states.append((item.date, status.value, status))
    if not states:
        return None
    observed_at, _, status = max(states, key=lambda value: (value[0], value[1]))
    diagnostics.included_records["race_control"] = 1
    return TrackStatusState(status=status, observed_at=observed_at, provenance=(_source("race_control", observed_at, session_key, "race-control event reduced by explicit flag/message rules"),))


def reconstruct(dataset: OpenF1Dataset, session_key: int, focal_driver_number: int, decision_lap: int):
    diagnostics = ReconstructionDiagnostics(malformed_records=sum(part.malformed for part in dataset.__dict__.values()))
    session_candidates = sorted((s for s in dataset.sessions.records if s.session_key == session_key), key=_stable_record_key)
    if not session_candidates:
        raise ReconstructionFailure("OpenF1 session metadata is missing or unusable.")
    meta = session_candidates[0]
    if meta.year is None or not (meta.country_name or meta.location or meta.circuit_short_name) or not (meta.session_name or meta.session_type):
        raise ReconstructionFailure("Session metadata cannot establish canonical identity.")
    cutoff = decision_cutoff(dataset.laps.records, focal_driver_number, decision_lap)
    place = meta.country_name or meta.location or meta.circuit_short_name or ""
    event_name = f"{place} Grand Prix"
    eid = event_id(meta.year, place, event_name)
    sid = session_id(eid, meta.session_type or meta.session_name or "", meta.session_name or meta.session_type or "")
    event = Event(event_id=eid, name=event_name, circuit_id=meta.circuit_short_name, external_ids=(_external("meeting", meta.meeting_key),) if meta.meeting_key is not None else ())
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
    for driver in sorted(dataset.drivers.records, key=_stable_record_key):
        number = driver.driver_number
        if number is None or number in seen_numbers or (driver.session_key is not None and driver.session_key != session_key):
            diagnostics.duplicate_records += number in seen_numbers
            continue
        seen_numbers.add(number)
        deduped = {}
        for lap_no, completed, index, lap in laps_by_driver[number]:
            old = deduped.get(lap_no)
            if old is not None:
                diagnostics.duplicate_records += 1
            candidate = (completed, _stable_record_key(lap), lap)
            if old is None or candidate[:2] < old[:2]:
                deduped[lap_no] = candidate
        lap_rows = sorted(((no, *value) for no, value in deduped.items()), key=lambda value: (value[0], value[1]))
        position = _latest_dated(dataset.positions.records, number, cutoff, diagnostics, "position")
        interval = _latest_dated(dataset.intervals.records, number, cutoff, diagnostics, "intervals")
        pits = [p for p in dataset.pits.records if p.driver_number == number and p.date is not None and p.date <= cutoff]
        diagnostics.future_records += sum(1 for p in dataset.pits.records if p.driver_number == number and p.date is not None and p.date > cutoff)
        diagnostics.untimed_records += sum(1 for p in dataset.pits.records if p.driver_number == number and p.date is None)
        timestamps = ([lap_rows[-1][1]] if lap_rows else []) + ([position.date] if position else []) + ([interval.date] if interval else []) + [p.date for p in pits]
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
        if pits:
            provenance.append(_source("pit", max(p.date for p in pits), session_key, "timestamp-bounded pit events counted"))
        cars.append(CarState(
            competitor_id=competitor_id(sid, number), observed_at=max(timestamps), driver_id=None,
            driver_name=driver.full_name or " ".join(filter(None, (driver.first_name, driver.last_name))) or None,
            position=position.position if position and position.position and position.position > 0 else None,
            current_lap=current_lap, gap_ahead=parse_gap(interval.interval) if interval else None,
            gap_behind=None, gap_to_leader=parse_gap(interval.gap_to_leader) if interval else None,
            tyre=tyre, recent_laps=lap_observations, in_pit=None, pit_stop_count=len(pits),
            data_quality=_quality(missing, warnings), provenance=tuple(provenance),
            external_ids=(_external("driver_number", number),),
        ))
    if not cars:
        raise ReconstructionFailure("No competitor has timestamped evidence at or before the cutoff.")
    weather = _weather(dataset.weather.records, cutoff, session_key, diagnostics)
    status = _status(dataset.race_control.records, cutoff, session_key, diagnostics)
    if weather is None:
        field_missing.append("weather")
    if status is None:
        field_missing.append("track_status")
    if diagnostics.malformed_records:
        field_warnings.append("malformed provider records were ignored")
    if diagnostics.duplicate_records:
        field_warnings.append("duplicate provider records were resolved deterministically")
    if diagnostics.future_records:
        field_warnings.append("records after the observation cutoff were excluded")
    if diagnostics.untimed_records:
        field_warnings.append("records without defensible timestamps were excluded")
    if diagnostics.excluded_competitors:
        field_warnings.append("competitors without timestamped evidence were excluded")
    state = RaceState(
        session=session, observation_cutoff=cutoff, track_status=status, weather=weather,
        competitors=tuple(sorted(cars, key=lambda car: int(car.external_ids[0].value))),
        data_quality=_quality(field_missing, field_warnings),
        provenance=(_source("historical session datasets", cutoff, session_key, "full-field reconstruction bounded by focal completed-lap cutoff", "provider identifiers retained as metadata only"),),
    )
    return state, diagnostics
