"""Deterministic OpenF1-to-canonical modelling-history transformation."""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from math import isfinite

from app.domain_v2.enums import (
    DataQualityLevel,
    LapAdmissionRejectionReason,
    LapExclusionReason,
    LapQualityWarning,
    TrackStatus,
    TyreCompound,
)
from app.domain_v2.identity import CompetitorId
from app.domain_v2.modelling import GapEvidence, ModellingLapObservation, PaceEstimationContext, TrackStatusEvidence
from app.domain_v2.provenance import DataQuality, Provenance
from app.domain_v2.race_state import RaceState, WeatherState

from .dto import IntervalDTO, LapDTO, PitDTO, PositionDTO, RaceControlDTO, StintDTO, WeatherDTO
from .mapper import (
    OpenF1Dataset,
    _completed,
    _stable_record_key,
    _usable_weather,
    canonical_interval_gaps,
    global_track_status,
    track_status_precedence,
)


@dataclass
class ModellingHistoryDiagnostics:
    source_lap_rows: int = 0
    admitted_observations: int = 0
    admission_rejections: dict[LapAdmissionRejectionReason, int] = field(default_factory=dict)
    rows_bounded_out: int = 0
    foreign_session_rows: int = 0
    unmapped_competitor_rows: int = 0
    exact_duplicate_laps: int = 0
    conflicting_laps: int = 0
    future_stint_starts: int = 0
    ambiguous_stint_annotations: int = 0
    tyre_annotations: int = 0
    weather_alignments: int = 0
    race_control_alignments: int = 0
    gap_alignments: int = 0
    pit_lane_affected_observations: int = 0

    def reject(self, reason: LapAdmissionRejectionReason) -> None:
        self.admission_rejections[reason] = self.admission_rejections.get(reason, 0) + 1


@dataclass(frozen=True)
class AdmittedLap:
    competitor_id: CompetitorId
    driver_number: int
    lap: LapDTO
    started_at: datetime
    completed_at: datetime


@dataclass(frozen=True)
class StintAnnotation:
    compound: TyreCompound | None
    tyre_age_laps: int | None
    stint_number: int | None
    provenance: Provenance | None
    ambiguous: bool = False


def build_pace_context(
    race_state: RaceState,
    dataset: OpenF1Dataset,
    session_key: int,
) -> tuple[PaceEstimationContext, ModellingHistoryDiagnostics]:
    diagnostics = ModellingHistoryDiagnostics()
    driver_to_competitor = _canonical_driver_mapping(race_state)
    laps = _admit_laps(dataset.laps.records, session_key, race_state.observation_cutoff, driver_to_competitor, diagnostics)
    latest_lap = {driver: max(item.lap.lap_number for item in rows) for driver, rows in _by_driver(laps).items()}
    stints = _bounded_stints(dataset.stints.records, session_key, driver_to_competitor, latest_lap, diagnostics)
    cutoff = race_state.observation_cutoff
    weather = _weather_timeline(dataset.weather.records, session_key, cutoff, diagnostics)
    control = _control_timeline(dataset.race_control.records, session_key, cutoff, diagnostics)
    positions = _position_timelines(dataset.positions.records, session_key, cutoff, driver_to_competitor, diagnostics)
    intervals = _interval_timelines(dataset.intervals.records, session_key, cutoff, driver_to_competitor, diagnostics)
    pits = _pit_timelines(dataset.pits.records, session_key, driver_to_competitor, race_state.observation_cutoff, diagnostics)

    observations = []
    for admitted in sorted(laps, key=lambda item: (str(item.competitor_id), item.lap.lap_number)):
        annotation = _stint_for_lap(stints.get(admitted.driver_number, ()), admitted.lap.lap_number, session_key)
        if annotation.ambiguous:
            diagnostics.ambiguous_stint_annotations += 1
        if any(value is not None for value in (annotation.compound, annotation.tyre_age_laps, annotation.stint_number)):
            diagnostics.tyre_annotations += 1
        aligned_weather, weather_transition = _align_weather(weather, admitted.started_at, admitted.completed_at, session_key)
        status, caution_exclusions = _align_control(control, admitted.started_at, admitted.completed_at, session_key)
        gap = _align_gap(
            intervals.get(admitted.driver_number, ()), positions.get(admitted.driver_number, ()),
            admitted.completed_at, session_key,
        )
        exclusions = set(caution_exclusions)
        if admitted.lap.lap_number == 1:
            exclusions.add(LapExclusionReason.LAP_ONE)
        if admitted.lap.is_pit_out_lap is True:
            exclusions.add(LapExclusionReason.PIT_OUT)
        if _pit_affects_lap(pits.get(admitted.driver_number, ()), admitted):
            exclusions.add(LapExclusionReason.PIT_LANE_AFFECTED)
            diagnostics.pit_lane_affected_observations += 1
        warnings = (LapQualityWarning.WEATHER_TRANSITION,) if weather_transition else ()
        missing = []
        if annotation.compound is None or annotation.tyre_age_laps is None:
            missing.append("tyre_annotation")
        if status is None:
            missing.append("race_control_context")
        if aligned_weather is None:
            missing.append("weather_context")
        if gap is None:
            missing.append("gap_context")
        quality_warnings = ["OpenF1 lap completion is approximated from date_start + lap_duration"]
        if annotation.ambiguous:
            quality_warnings.append("conflicting bounded stint evidence; tyre annotation omitted")
        quality = DataQuality(
            level=DataQualityLevel.DEGRADED if missing or quality_warnings else DataQualityLevel.GOOD,
            completeness=None,
            warnings=tuple(quality_warnings),
            missing_fields=tuple(missing),
        )
        provenance = [
            _provenance("laps", admitted.completed_at, session_key, "lap completion derived from date_start + lap_duration"),
        ]
        if annotation.provenance is not None:
            provenance.append(annotation.provenance)
        observations.append(ModellingLapObservation(
            competitor_id=admitted.competitor_id,
            lap_number=admitted.lap.lap_number,
            completed_at=admitted.completed_at,
            lap_time_s=admitted.lap.lap_duration,
            compound=annotation.compound,
            tyre_age_laps=annotation.tyre_age_laps,
            stint_number=annotation.stint_number,
            track_status=status,
            weather=aligned_weather,
            gap_evidence=gap,
            hard_exclusions=tuple(reason for reason in LapExclusionReason if reason in exclusions),
            quality_warnings=warnings,
            data_quality=quality,
            provenance=tuple(provenance),
        ))
        diagnostics.weather_alignments += aligned_weather is not None
        diagnostics.race_control_alignments += status is not None
        diagnostics.gap_alignments += gap is not None

    diagnostics.admitted_observations = len(observations)
    context_warnings = list(race_state.data_quality.warnings)
    if diagnostics.conflicting_laps:
        context_warnings.append("conflicting timed lap evidence was omitted")
    if diagnostics.ambiguous_stint_annotations:
        context_warnings.append("some tyre annotations were omitted because bounded stint evidence conflicted")
    if observations:
        context_warnings.append("OpenF1 lap completion is approximated from date_start + lap_duration")
    context_warnings = sorted(set(context_warnings))
    context_missing = tuple(sorted(set(race_state.data_quality.missing_fields)))
    if race_state.data_quality.level is DataQualityLevel.INSUFFICIENT:
        context_level = DataQualityLevel.INSUFFICIENT
    elif observations or context_warnings or context_missing:
        context_level = DataQualityLevel.DEGRADED
    else:
        context_level = race_state.data_quality.level
    context = PaceEstimationContext(
        race_state=race_state,
        as_of=race_state.observation_cutoff,
        observations=tuple(observations),
        data_quality=DataQuality(
            level=context_level,
            completeness=None,
            warnings=tuple(context_warnings),
            missing_fields=context_missing,
        ),
        provenance=(_provenance(
            "OpenF1 historical session datasets", race_state.observation_cutoff, session_key,
            "full-field modelling history bounded by canonical RaceState cutoff",
            "provider identifiers mapped to existing canonical competitors",
        ),),
    )
    return context, diagnostics


def _canonical_driver_mapping(race_state: RaceState) -> dict[int, CompetitorId]:
    result = {}
    for car in race_state.competitors:
        values = [item.value for item in car.external_ids if item.provider.lower() == "openf1" and item.resource_type == "driver_number"]
        if len(values) == 1:
            try:
                result[int(values[0])] = car.competitor_id
            except ValueError:
                continue
    return result


def _admit_laps(records, session_key, cutoff, mapping, diagnostics):
    usable = defaultdict(list)
    diagnostics.source_lap_rows = len(records)
    for lap in records:
        if lap.session_key is not None and lap.session_key != session_key:
            diagnostics.foreign_session_rows += 1
            continue
        if lap.driver_number not in mapping:
            diagnostics.unmapped_competitor_rows += 1
            continue
        if isinstance(lap.lap_number, bool) or not isinstance(lap.lap_number, int) or lap.lap_number < 1:
            diagnostics.reject(LapAdmissionRejectionReason.INVALID_LAP_NUMBER)
            continue
        if lap.date_start is None or lap.lap_duration is None:
            diagnostics.reject(LapAdmissionRejectionReason.MISSING_TIMING)
            continue
        if not isfinite(lap.lap_duration) or lap.lap_duration <= 0:
            diagnostics.reject(LapAdmissionRejectionReason.INVALID_DURATION)
            continue
        completed = _completed(lap)
        if completed is None:
            diagnostics.reject(LapAdmissionRejectionReason.INVALID_DURATION)
            continue
        if completed > cutoff:
            diagnostics.rows_bounded_out += 1
            continue
        usable[(mapping[lap.driver_number], lap.driver_number, lap.lap_number)].append((lap, completed))
    admitted = []
    for (competitor, driver, _), rows in usable.items():
        unique = {_stable_record_key(lap): (lap, completed) for lap, completed in rows}
        diagnostics.exact_duplicate_laps += len(rows) - len(unique)
        if len(unique) != 1:
            diagnostics.conflicting_laps += 1
            diagnostics.reject(LapAdmissionRejectionReason.CONFLICTING_TIMING_EVIDENCE)
            continue
        lap, completed = next(iter(unique.values()))
        admitted.append(AdmittedLap(competitor, driver, lap, lap.date_start, completed))
    return admitted


def _bounded_stints(records, session_key, mapping, latest_lap, diagnostics):
    grouped = defaultdict(dict)
    for stint in records:
        if stint.session_key is not None and stint.session_key != session_key:
            diagnostics.foreign_session_rows += 1
            continue
        if stint.driver_number not in mapping:
            diagnostics.unmapped_competitor_rows += 1
            continue
        if stint.lap_start is None or stint.lap_start < 1:
            continue
        if stint.lap_start > latest_lap.get(stint.driver_number, 0):
            diagnostics.future_stint_starts += 1
            continue
        grouped[stint.driver_number][_stable_record_key(stint)] = stint
    return {
        driver: tuple(sorted(rows.values(), key=lambda item: (item.lap_start, item.stint_number or 0, _stable_record_key(item))))
        for driver, rows in grouped.items()
    }


def _stint_for_lap(stints, lap_number, session_key):
    applicable = [item for item in stints if item.lap_start <= lap_number]
    if not applicable:
        return StintAnnotation(None, None, None, None)
    latest_start = max(item.lap_start for item in applicable)
    candidates = [item for item in applicable if item.lap_start == latest_start]
    semantic = {(item.compound, item.tyre_age_at_start, item.stint_number) for item in candidates}
    if len(semantic) != 1:
        return StintAnnotation(None, None, None, None, ambiguous=True)
    item = candidates[0]
    if item.tyre_age_at_start is None or item.tyre_age_at_start < 0 or (
        item.stint_number is not None and item.stint_number < 1
    ):
        return StintAnnotation(None, None, None, None)
    compounds = {compound.value.upper(): compound for compound in TyreCompound}
    compound = None if item.compound is None else compounds.get(item.compound.upper(), TyreCompound.UNKNOWN)
    age = item.tyre_age_at_start + lap_number - item.lap_start + 1
    return StintAnnotation(
        compound, age, item.stint_number,
        _provenance(
            "stints", None, session_key,
            "untimestamped stint start admitted only because lap_start was bounded by competitor state at cutoff",
            "tyre age reconstructed from tyre_age_at_start; provider lap_end ignored",
        ),
    )


def _weather_timeline(records, session_key, cutoff, diagnostics):
    unique = {}
    for item in records:
        if item.session_key is not None and item.session_key != session_key:
            diagnostics.foreign_session_rows += 1
        elif item.date is not None and item.date > cutoff:
            diagnostics.rows_bounded_out += 1
        elif item.date is not None and _usable_weather(item):
            unique[_stable_record_key(item)] = item
    return tuple(sorted(unique.values(), key=lambda item: (item.date, _stable_record_key(item))))


def _weather_state(item: WeatherDTO, session_key: int) -> WeatherState:
    return WeatherState(
        observed_at=item.date,
        air_temperature_c=item.air_temperature,
        track_temperature_c=item.track_temperature,
        humidity_fraction=item.humidity / 100 if item.humidity is not None else None,
        wind_speed_mps=item.wind_speed,
        rainfall_detected=bool(item.rainfall) if item.rainfall is not None else None,
        provenance=(_provenance("weather", item.date, session_key, "humidity percent converted to fraction"),),
    )


def _align_weather(timeline, started_at, completed_at, session_key):
    eligible = [item for item in timeline if item.date <= completed_at]
    if not eligible:
        return None, False
    chosen = eligible[-1]
    before = [item for item in timeline if item.date <= started_at and item.rainfall is not None]
    during = [item for item in timeline if started_at < item.date <= completed_at and item.rainfall is not None]
    transition = bool(before and any(bool(item.rainfall) != bool(before[-1].rainfall) for item in during))
    return _weather_state(chosen, session_key), transition


def _control_timeline(records, session_key, cutoff, diagnostics):
    by_time = defaultdict(list)
    for item in records:
        if item.session_key is not None and item.session_key != session_key:
            diagnostics.foreign_session_rows += 1
            continue
        if item.date is not None and item.date > cutoff:
            diagnostics.rows_bounded_out += 1
            continue
        if item.date is not None and (status := global_track_status(item)) is not None:
            by_time[item.date].append((track_status_precedence(status), _stable_record_key(item), status))
    return tuple((at, max(values)[2]) for at, values in sorted(by_time.items()))


def _align_control(timeline, started_at, completed_at, session_key):
    eligible = [(at, status) for at, status in timeline if at <= completed_at]
    if not eligible:
        return None, ()
    at, status = eligible[-1]
    evidence = TrackStatusEvidence(
        observed_at=at,
        status=status,
        provenance=(_provenance("race_control", at, session_key, "accepted V2.1 global race-control reducer"),),
    )
    active_at_start = [(event_at, value) for event_at, value in timeline if event_at <= started_at]
    overlap = ([active_at_start[-1][1]] if active_at_start else []) + [
        value for event_at, value in timeline if started_at < event_at <= completed_at
    ]
    mapping = {
        TrackStatus.SAFETY_CAR: LapExclusionReason.SAFETY_CAR,
        TrackStatus.VSC: LapExclusionReason.VSC,
        TrackStatus.RED: LapExclusionReason.RED_FLAG,
        TrackStatus.YELLOW: LapExclusionReason.GLOBAL_YELLOW,
    }
    return evidence, tuple(mapping[value] for value in overlap if value in mapping)


def _position_timelines(records, session_key, cutoff, mapping, diagnostics):
    grouped = defaultdict(dict)
    for item in records:
        if item.session_key is not None and item.session_key != session_key:
            diagnostics.foreign_session_rows += 1
        elif item.date is not None and item.date > cutoff:
            diagnostics.rows_bounded_out += 1
        elif item.driver_number not in mapping:
            diagnostics.unmapped_competitor_rows += 1
        elif item.date is not None and isinstance(item.position, int) and not isinstance(item.position, bool) and item.position > 0:
            grouped[item.driver_number][_stable_record_key(item)] = item
    return {driver: tuple(sorted(rows.values(), key=lambda item: (item.date, _stable_record_key(item)))) for driver, rows in grouped.items()}


def _interval_timelines(records, session_key, cutoff, mapping, diagnostics):
    grouped = defaultdict(dict)
    for item in records:
        if item.session_key is not None and item.session_key != session_key:
            diagnostics.foreign_session_rows += 1
        elif item.date is not None and item.date > cutoff:
            diagnostics.rows_bounded_out += 1
        elif item.driver_number not in mapping:
            diagnostics.unmapped_competitor_rows += 1
        elif item.date is not None:
            grouped[item.driver_number][_stable_record_key(item)] = item
    return {driver: tuple(sorted(rows.values(), key=lambda item: (item.date, _stable_record_key(item)))) for driver, rows in grouped.items()}


def _align_gap(intervals, positions, completed_at, session_key):
    bounded_positions = [item for item in positions if item.date <= completed_at]
    leader = bool(bounded_positions and bounded_positions[-1].position == 1)
    for item in reversed([row for row in intervals if row.date <= completed_at]):
        gaps = canonical_interval_gaps(item, leader)
        if gaps is None:
            continue
        ahead, to_leader = gaps
        return GapEvidence(
            observed_at=item.date,
            gap_ahead=ahead,
            gap_to_leader=to_leader,
            provenance=(_provenance(
                "intervals", item.date, session_key,
                "latest usable interval no later than lap completion",
                "leader gap_ahead normalized to missing" if leader else "provider gap mapped to canonical dimensional value",
            ),),
        )
    return None


def _pit_timelines(records, session_key, mapping, cutoff, diagnostics):
    grouped = defaultdict(dict)
    for item in records:
        if item.session_key is not None and item.session_key != session_key:
            diagnostics.foreign_session_rows += 1
        elif item.driver_number not in mapping:
            diagnostics.unmapped_competitor_rows += 1
        elif item.date is not None and item.date > cutoff:
            diagnostics.rows_bounded_out += 1
        elif item.date is not None:
            grouped[item.driver_number][_stable_record_key(item)] = item
    return {driver: tuple(sorted(rows.values(), key=lambda item: (item.date, _stable_record_key(item)))) for driver, rows in grouped.items()}


def _pit_affects_lap(pits: tuple[PitDTO, ...], admitted: AdmittedLap) -> bool:
    return any(
        item.lap_number == admitted.lap.lap_number and admitted.started_at <= item.date <= admitted.completed_at
        for item in pits
    )


def _by_driver(items):
    result = defaultdict(list)
    for item in items:
        result[item.driver_number].append(item)
    return result


def _provenance(resource, observed_at, session_key, *transformations):
    return Provenance(
        source="OpenF1",
        source_version="v1",
        observed_at=observed_at,
        transformations=transformations,
        assumptions=(f"OpenF1 session key {session_key} retained only at adapter boundary",),
    )
