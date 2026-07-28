import logging
import random
from datetime import datetime, timedelta, timezone
from statistics import mean, pstdev

from app.data_sources.openf1_client import OpenF1Client
from app.models.replay import (
    AlternativeStrategyComparison,
    DriverSummary,
    HistoricalSession,
    LapRecord,
    PaceSummary,
    RaceControlEvent,
    RaceControlSummary,
    RecordCount,
    ReplayAssessment,
    ReplayDataQuality,
    ReplayRequest,
    ReplaySnapshot,
    StintRecord,
    StrategyRecommendation,
    WeatherSample,
    WeatherSummary,
)

logger = logging.getLogger("racebrain.replay")
client = OpenF1Client()

# Educational defaults only. They are deliberately simple model assumptions,
# not circuit-accurate pit-lane measurements.
GREEN_FLAG_PIT_LOSS_SECONDS = 22.0
SAFETY_CAR_PIT_LOSS_SECONDS = 12.0
PIT_LOSS_STD_DEV_SECONDS = 1.2


class ReplayValidationError(ValueError):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def _parse_many(model, records: list[dict]) -> tuple[list, int]:
    parsed = []
    ignored = 0
    for record in records:
        try:
            parsed.append(model.model_validate(record))
        except (ValueError, TypeError):
            ignored += 1
    return parsed, ignored


def _normalise_laps(laps: list[LapRecord]) -> tuple[list[LapRecord], int]:
    by_number: dict[int, LapRecord] = {}
    duplicates = 0
    for lap in laps:
        existing = by_number.get(lap.lap_number)
        if existing is None:
            by_number[lap.lap_number] = lap
            continue
        duplicates += 1
        candidates = [existing, lap]
        by_number[lap.lap_number] = min(
            candidates,
            key=lambda item: (
                item.date_start is None,
                item.date_start or datetime.max.replace(tzinfo=timezone.utc),
                item.lap_duration is None,
                item.lap_duration or float("inf"),
            ),
        )
    return sorted(by_number.values(), key=lambda item: item.lap_number), duplicates


def available_decision_laps(session_key: int, driver_number: int) -> list[int]:
    raw_laps = client.get_laps(session_key, driver_number)
    laps, _ = _parse_many(LapRecord, raw_laps)
    laps, _ = _normalise_laps(laps)
    return sorted(
        {
            lap.lap_number
            for lap in laps
            if lap.lap_duration is not None and lap.lap_duration > 0
        }
    )


def _pace_summary(laps: list[LapRecord]) -> PaceSummary:
    durations = [
        lap.lap_duration
        for lap in laps
        if lap.lap_duration is not None and not lap.is_pit_out_lap
    ]
    recent = durations[-5:]
    previous = durations[-10:-5]
    recent_average = round(mean(recent), 3) if recent else None
    previous_average = round(mean(previous), 3) if previous else None
    delta = (
        round(recent_average - previous_average, 3)
        if recent_average is not None and previous_average is not None
        else None
    )
    if delta is None:
        trend = "unknown"
    elif delta > 0.35:
        trend = "degrading"
    elif delta < -0.35:
        trend = "improving"
    else:
        trend = "stable"
    return PaceSummary(
        recent_lap_times=[round(value, 3) for value in recent],
        recent_average=recent_average,
        previous_average=previous_average,
        trend_seconds_per_lap=delta,
        trend=trend,
    )


def _weather_summary(weather: list[WeatherSample]) -> WeatherSummary:
    if not weather:
        return WeatherSummary()
    latest = weather[-1]
    rainfall = any(bool(item.rainfall) for item in weather[-3:])
    return WeatherSummary(
        air_temperature=latest.air_temperature,
        track_temperature=latest.track_temperature,
        humidity=latest.humidity,
        wind_speed=latest.wind_speed,
        rainfall_detected=rainfall,
        trend="rain_detected" if rainfall else "dry",
    )


def _race_control_summary(events: list[RaceControlEvent]) -> RaceControlSummary:
    messages = [event.message or "" for event in events]
    safety_events = [message for message in messages if "SAFETY CAR" in message.upper()]
    red_events = [message for message in messages if "RED FLAG" in message.upper()]
    safety_active = False
    red_active = False
    for raw_message in messages:
        message = raw_message.upper()
        if any(
            phrase in message
            for phrase in ("SAFETY CAR DEPLOYED", "VIRTUAL SAFETY CAR DEPLOYED")
        ):
            safety_active = True
        if any(
            phrase in message
            for phrase in (
                "SAFETY CAR IN",
                "VIRTUAL SAFETY CAR ENDING",
                "GREEN FLAG",
                "TRACK CLEAR",
                "DRS ENABLED",
            )
        ):
            safety_active = False
        if "RED FLAG" in message or "SESSION SUSPENDED" in message:
            red_active = True
        if any(
            phrase in message
            for phrase in (
                "RACE RESUMED",
                "SESSION RESUMED",
                "GREEN FLAG",
                "DRS ENABLED",
            )
        ):
            red_active = False
    return RaceControlSummary(
        safety_car_active=safety_active,
        red_flag_active=red_active,
        safety_car_events=len(safety_events),
        red_flag_events=len(red_events),
        recent_messages=[message for message in messages[-5:] if message],
    )


def build_replay_snapshot(request: ReplayRequest) -> ReplaySnapshot:
    logger.info(
        "replay_request",
        extra={
            "session_key": request.session_key,
            "driver_number": request.driver_number,
            "decision_lap": request.decision_lap,
        },
    )
    cache_hits: dict[str, bool] = {}

    raw_sessions = client.get_sessions(session_key=request.session_key)
    cache_hits["sessions"] = client.last_cache_hit
    sessions, invalid_sessions = _parse_many(HistoricalSession, raw_sessions)
    if not sessions:
        raise ReplayValidationError("Unknown historical session.", status_code=404)

    raw_drivers = client.get_drivers(request.session_key)
    cache_hits["drivers"] = client.last_cache_hit
    drivers, invalid_drivers = _parse_many(DriverSummary, raw_drivers)
    driver = next(
        (item for item in drivers if item.driver_number == request.driver_number),
        None,
    )
    if driver is None:
        raise ReplayValidationError("Unknown driver for this session.", status_code=404)

    raw_laps = client.get_laps(request.session_key, request.driver_number)
    cache_hits["laps"] = client.last_cache_hit
    laps, invalid_laps = _parse_many(LapRecord, raw_laps)
    laps, duplicate_laps = _normalise_laps(laps)
    completed_laps = sorted(
        [
            lap
            for lap in laps
            if lap.lap_duration is not None and lap.lap_duration > 0
        ],
        key=lambda item: item.lap_number,
    )
    available_laps = sorted({lap.lap_number for lap in completed_laps})
    unusable_laps = invalid_laps + duplicate_laps + len(laps) - len(completed_laps)
    if request.decision_lap not in available_laps:
        raise ReplayValidationError(
            "Decision lap must be one of the driver's available completed laps."
        )

    decision_record = next(
        lap for lap in completed_laps if lap.lap_number == request.decision_lap
    )
    warnings: list[str] = []
    if decision_record.date_start and decision_record.lap_duration:
        cutoff = decision_record.date_start + timedelta(seconds=decision_record.lap_duration)
        cutoff_source = "lap_completion_timestamp"
    else:
        cutoff = None
        cutoff_source = "lap_number_only"
        warnings.append(
            "Lap timestamps were unavailable; timestamp-only context was excluded."
        )

    bounded_laps = [lap for lap in completed_laps if lap.lap_number <= request.decision_lap]
    future_laps = [lap for lap in completed_laps if lap.lap_number > request.decision_lap]

    raw_stints = client.get_stints(request.session_key, request.driver_number)
    cache_hits["stints"] = client.last_cache_hit
    stints, invalid_stints = _parse_many(StintRecord, raw_stints)
    bounded_stints = []
    future_stints = []
    for stint in stints:
        if stint.lap_start > request.decision_lap:
            future_stints.append(stint)
            continue
        bounded_stints.append(
            stint.model_copy(
                update={
                    "lap_end": min(
                        stint.lap_end or request.decision_lap,
                        request.decision_lap,
                    )
                }
            )
        )
    active_stints = [
        stint
        for stint in stints
        if stint.lap_start <= request.decision_lap
        and (stint.lap_end is None or stint.lap_end >= request.decision_lap)
    ]
    current_stint_unbounded = max(
        active_stints,
        key=lambda item: (item.lap_start, item.stint_number or 0),
        default=None,
    )
    current_stint = (
        current_stint_unbounded.model_copy(update={"lap_end": request.decision_lap})
        if current_stint_unbounded
        else None
    )
    estimated_tyre_age = None
    if current_stint:
        estimated_tyre_age = max(
            0,
            (current_stint.tyre_age_at_start or 0)
            + request.decision_lap
            - current_stint.lap_start
            + 1,
        )
    else:
        warnings.append("No valid stint covered the selected decision lap.")

    raw_weather = client.get_weather(request.session_key)
    cache_hits["weather"] = client.last_cache_hit
    weather, invalid_weather = _parse_many(WeatherSample, raw_weather)
    weather.sort(key=lambda item: (item.date is None, item.date))
    bounded_weather = [
        item for item in weather if cutoff is not None and item.date and item.date <= cutoff
    ]
    future_weather = [
        item for item in weather if cutoff is not None and item.date and item.date > cutoff
    ]
    unusable_weather = [
        item
        for item in weather
        if item.date is None or (cutoff is None and item.date is not None)
    ]
    if not bounded_weather:
        warnings.append("No weather sample could be proven available by the cutoff.")

    raw_control = client.get_race_control(request.session_key)
    cache_hits["race_control"] = client.last_cache_hit
    events, invalid_events = _parse_many(RaceControlEvent, raw_control)
    events.sort(
        key=lambda item: (
            item.date is None,
            item.date,
            item.lap_number is None,
            item.lap_number,
        )
    )
    bounded_events = []
    future_events = []
    unusable_events = []
    for event in events:
        is_future_lap = event.lap_number is not None and event.lap_number > request.decision_lap
        is_future_time = cutoff is not None and event.date is not None and event.date > cutoff
        timestamp_unknown = cutoff is None and event.lap_number is None
        context_unknown = event.date is None and event.lap_number is None
        if is_future_lap or is_future_time:
            future_events.append(event)
        elif timestamp_unknown or context_unknown:
            unusable_events.append(event)
        else:
            bounded_events.append(event)

    invalid_counts = invalid_sessions + invalid_drivers
    if invalid_counts:
        warnings.append(f"{invalid_counts} malformed session or driver records were ignored.")
    malformed_context = (
        unusable_laps + invalid_stints + invalid_weather + invalid_events
        + len(unusable_weather)
        + len(unusable_events)
    )
    if malformed_context:
        warnings.append(
            f"{malformed_context} incomplete or malformed context records were ignored."
        )

    latest_timestamp = max(
        [
            value
            for value in (
                [lap.date_start for lap in bounded_laps]
                + [item.date for item in bounded_weather]
                + [event.date for event in bounded_events]
            )
            if value is not None
        ],
        default=None,
    )

    snapshot = ReplaySnapshot(
        session=sessions[0].model_copy(update={"date_end": None}),
        driver=driver,
        decision_lap=request.decision_lap,
        available_decision_laps=[
            lap for lap in available_laps if lap <= request.decision_lap
        ],
        cutoff_timestamp=cutoff,
        current_stint=current_stint,
        current_compound=current_stint.compound if current_stint else None,
        estimated_tyre_age=estimated_tyre_age,
        pace=_pace_summary(bounded_laps),
        weather=_weather_summary(bounded_weather),
        race_control=_race_control_summary(bounded_events),
        bounded_laps=bounded_laps,
        bounded_stints=bounded_stints,
        data_quality=ReplayDataQuality(
            cutoff_source=cutoff_source,
            latest_included_timestamp=latest_timestamp,
            records={
                "laps": RecordCount(
                    included=len(bounded_laps),
                    ignored_future=len(future_laps),
                    ignored_unusable=unusable_laps,
                ),
                "stints": RecordCount(
                    included=len(bounded_stints),
                    ignored_future=len(future_stints),
                    ignored_unusable=invalid_stints,
                ),
                "weather": RecordCount(
                    included=len(bounded_weather),
                    ignored_future=len(future_weather),
                    ignored_unusable=invalid_weather + len(unusable_weather),
                ),
                "race_control": RecordCount(
                    included=len(bounded_events),
                    ignored_future=len(future_events),
                    ignored_unusable=invalid_events + len(unusable_events),
                ),
            },
            warnings=warnings,
            cache_hits=cache_hits,
        ),
    )
    logger.info(
        "replay_snapshot",
        extra={
            "session_key": request.session_key,
            "decision_lap": request.decision_lap,
            "cutoff": cutoff.isoformat() if cutoff else None,
            "included_counts": {
                key: value.included for key, value in snapshot.data_quality.records.items()
            },
        },
    )
    return snapshot


def _tyre_risk(compound: str | None, age: int | None) -> str:
    if not compound or age is None:
        return "unknown"
    threshold = {"SOFT": 18, "MEDIUM": 28, "HARD": 42}.get(compound.upper(), 30)
    if age >= threshold:
        return "high"
    if age >= threshold * 0.7:
        return "medium"
    return "low"


def recommend_strategy(snapshot: ReplaySnapshot) -> StrategyRecommendation:
    tyre_risk = _tyre_risk(snapshot.current_compound, snapshot.estimated_tyre_age)
    pace = snapshot.pace.trend
    weather = snapshot.weather
    control = snapshot.race_control

    if control.red_flag_active:
        recommendation = "keep_flexible"
        summary = "Keep the strategy flexible while the race is interrupted."
    elif control.safety_car_active:
        if tyre_risk in ("medium", "high"):
            recommendation = "box_now"
            summary = "Box now: the interruption reduces the relative pit-loss risk."
        else:
            recommendation = "keep_flexible"
            summary = "Keep flexible while the safety-car opportunity and tyre state are assessed."
    elif weather.rainfall_detected:
        recommendation = "monitor_weather"
        summary = "Monitor weather and avoid committing beyond the current evidence."
    elif tyre_risk == "high" or pace == "degrading":
        recommendation = "pit_window_opening"
        summary = "The pit window is opening as tyre and pace risk increase."
    elif tyre_risk == "medium":
        recommendation = "preserve_tyres"
        summary = "Preserve tyres while keeping the next pit window available."
    elif pace == "improving":
        recommendation = "extend"
        summary = "Extend the stint while recent pace remains constructive."
    else:
        recommendation = "hold"
        summary = "Hold the current plan; no bounded signal justifies an immediate stop."

    signals = sum(
        [
            snapshot.current_stint is not None,
            snapshot.pace.recent_average is not None,
            snapshot.data_quality.records["weather"].included > 0,
            snapshot.data_quality.records["race_control"].included > 0,
        ]
    )
    confidence = "high" if signals == 4 and not snapshot.data_quality.warnings else (
        "medium" if signals >= 2 else "low"
    )
    result = StrategyRecommendation(
        recommendation=recommendation,
        confidence=confidence,
        summary=summary,
        tyre_risk=tyre_risk,
        reasoning_factors=[
            f"Current tyre risk is {tyre_risk}.",
            f"Recent pace trend is {pace}.",
            f"Rain was {'detected' if weather.rainfall_detected else 'not detected'} by the cutoff.",
            f"Safety-car context was {'active' if control.safety_car_active else 'not active'} at this moment.",
        ],
        evidence={
            "decision_lap": snapshot.decision_lap,
            "compound": snapshot.current_compound,
            "estimated_tyre_age": snapshot.estimated_tyre_age,
            "recent_average_lap": snapshot.pace.recent_average,
            "pace_delta_seconds": snapshot.pace.trend_seconds_per_lap,
            "rainfall_detected": weather.rainfall_detected,
            "safety_car_active": control.safety_car_active,
        },
        limitations=[
            "No competitor traffic, gaps, undercut model, or final outcome is used.",
            *snapshot.data_quality.warnings,
        ],
    )
    logger.info(
        "replay_recommendation",
        extra={"recommendation": result.recommendation, "confidence": result.confidence},
    )
    return result


def compare_alternatives(
    snapshot: ReplaySnapshot,
    recommendation: StrategyRecommendation,
    *,
    seed: int | None,
    simulations: int,
    extend_laps: int,
) -> tuple[list[AlternativeStrategyComparison], str]:
    rng = random.Random(seed)
    base_lap = snapshot.pace.recent_average or 90.0
    age = snapshot.estimated_tyre_age or 0
    compound = (snapshot.current_compound or "MEDIUM").upper()
    degradation = {"SOFT": 0.16, "MEDIUM": 0.10, "HARD": 0.07}.get(compound, 0.10)
    pit_loss_baseline = (
        SAFETY_CAR_PIT_LOSS_SECONDS
        if snapshot.race_control.safety_car_active
        else GREEN_FLAG_PIT_LOSS_SECONDS
    )

    scores = {"pit_now": [], "extend": [], "hold": []}
    for _ in range(simulations):
        pace_noise = rng.gauss(0, 0.25)
        pit_noise = rng.gauss(0, PIT_LOSS_STD_DEV_SECONDS)
        pit_loss = max(0.0, pit_loss_baseline + pit_noise)
        shared_base = base_lap + pace_noise
        scores["pit_now"].append(pit_loss + extend_laps * (shared_base - 0.15))
        scores["extend"].append(
            sum(shared_base + degradation * (age + lap) for lap in range(extend_laps))
        )
        hold_laps = max(1, extend_laps // 2)
        scores["hold"].append(
            sum(
                shared_base + degradation * (age + lap)
                for lap in range(hold_laps)
            )
            + pit_loss
            + sum(
                shared_base - 0.15 + degradation * lap
                for lap in range(extend_laps - hold_laps)
            )
        )

    averages = {key: mean(values) for key, values in scores.items()}
    best = min(averages, key=averages.get)
    risk_map = {
        "pit_now": "low",
        "extend": "high" if recommendation.tyre_risk in ("medium", "high") else "medium",
        "hold": recommendation.tyre_risk,
    }
    results = [
        AlternativeStrategyComparison(
            alternative=key,
            strategy_score=round(value, 3),
            delta_to_recommended=round(value - averages[best], 3),
            uncertainty=round(pstdev(scores[key]), 3),
            tyre_risk=risk_map[key],
            explanation={
                "pit_now": "Stops immediately and pays an estimated pit-loss cost.",
                "extend": f"Runs {extend_laps} more laps with bounded tyre-age degradation.",
                "hold": "Keeps the current plan, then stops midway through the shared horizon.",
            }[key],
        )
        for key, value in sorted(averages.items(), key=lambda item: item[1])
    ]
    return results, best


def build_replay_assessment(request: ReplayRequest) -> ReplayAssessment:
    snapshot = build_replay_snapshot(request)
    recommendation = recommend_strategy(snapshot)
    alternatives, recommended_alternative = compare_alternatives(
        snapshot,
        recommendation,
        seed=request.seed,
        simulations=request.simulations,
        extend_laps=request.extend_laps,
    )
    return ReplayAssessment(
        snapshot=snapshot,
        recommendation=recommendation,
        alternatives=alternatives,
        recommended_alternative=recommended_alternative,
        seed=request.seed,
        simulations=request.simulations,
    )
