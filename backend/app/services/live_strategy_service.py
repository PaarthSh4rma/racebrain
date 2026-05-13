def get_current_stint(stints: list[dict]) -> dict | None:
    if not stints:
        return None

    valid = [
        stint for stint in stints
        if stint.get("lap_start") is not None
    ]

    if not valid:
        return stints[-1]

    return max(valid, key=lambda stint: stint.get("stint_number", 0))


def assess_tyre_risk(current_stint: dict | None) -> str:
    if not current_stint:
        return "unknown"

    lap_start = current_stint.get("lap_start") or 1
    lap_end = current_stint.get("lap_end") or lap_start
    tyre_age_start = current_stint.get("tyre_age_at_start") or 0

    stint_length = max(lap_end - lap_start, 0)
    estimated_age = tyre_age_start + stint_length

    compound = str(current_stint.get("compound", "")).upper()

    if compound == "SOFT" and estimated_age >= 18:
        return "high"
    if compound == "MEDIUM" and estimated_age >= 28:
        return "medium"
    if compound == "HARD" and estimated_age >= 45:
        return "medium"

    return "low"


def assess_race_volatility(race_state: dict) -> str:
    race_control = race_state.get("race_control_summary", {})
    weather = race_state.get("weather_summary", {})

    score = 0

    if race_control.get("safety_car_events", 0) > 0:
        score += 2

    if race_control.get("red_flag_events", 0) > 0:
        score += 2

    if weather.get("rainfall_detected"):
        score += 2

    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def generate_live_strategy_call(race_state: dict) -> dict:
    current_stint = get_current_stint(race_state.get("stints", []))
    tyre_risk = assess_tyre_risk(current_stint)
    volatility = assess_race_volatility(race_state)

    lap_summary = race_state.get("driver_lap_summary", {})
    weather = race_state.get("weather_summary", {})

    recommendation = "hold_position"
    call = "Hold position and continue monitoring."

    if tyre_risk == "high":
        recommendation = "pit_window_open"
        call = "Pit window is open. Tyre risk is high, so boxing soon should be considered."

    elif tyre_risk == "medium" and volatility in ["medium", "high"]:
        recommendation = "keep_flexible"
        call = "Keep strategy flexible. Tyre risk and race volatility are both meaningful."

    elif volatility == "high":
        recommendation = "delay_commitment"
        call = "Avoid committing too early. Race volatility is high."

    return {
        "recommendation": recommendation,
        "call": call,
        "tyre_risk": tyre_risk,
        "race_volatility": volatility,
        "current_stint": current_stint,
        "pace_context": {
            "laps_completed": lap_summary.get("laps_completed"),
            "average_lap_time": lap_summary.get("average_lap_time"),
            "best_lap_time": lap_summary.get("best_lap_time"),
        },
        "weather_context": weather,
        "reasoning": [
            f"Tyre risk assessed as {tyre_risk}.",
            f"Race volatility assessed as {volatility}.",
            f"Average lap time: {lap_summary.get('average_lap_time')}.",
            f"Track temperature average: {weather.get('track_temperature_avg')}°C.",
        ],
    }