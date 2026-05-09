import re


def parse_scenario_adjustments(question: str) -> dict:
    lowered = question.lower()

    adjustments = {}

    # -------------------------
    # Tyre degradation scenarios
    # -------------------------
    deg_match = re.search(
        r"degradation.*?(\d+)%",
        lowered,
    )

    if deg_match:
        percent = int(deg_match.group(1))
        adjustments["degradation_multiplier"] = 1 + (percent / 100)

    elif "degradation" in lowered and (
        "increase" in lowered
        or "higher" in lowered
        or "worse" in lowered
        or "more" in lowered
    ):
        adjustments["degradation_multiplier"] = 1.2

    elif "degradation" in lowered and (
        "decrease" in lowered
        or "lower" in lowered
        or "better" in lowered
        or "less" in lowered
    ):
        adjustments["degradation_multiplier"] = 0.8

    # -------------------------
    # Safety car scenarios
    # -------------------------
    sc_percent_match = re.search(
        r"safety car.*?(\d+)%",
        lowered,
    )

    if sc_percent_match:
        percent = int(sc_percent_match.group(1))
        adjustments["safety_car_probability"] = percent / 100

    elif "safety car" in lowered and (
        "drop" in lowered
        or "decrease" in lowered
        or "lower" in lowered
        or "less" in lowered
        or "fewer" in lowered
    ):
        adjustments["safety_car_probability"] = 0.15

    elif "safety car" in lowered and (
        "increase" in lowered
        or "higher" in lowered
        or "more" in lowered
        or "chaos" in lowered
    ):
        adjustments["safety_car_probability"] = 0.5

    # -------------------------
    # Weather semantics
    # -------------------------
    if (
        "rain" in lowered
        or "rains" in lowered
        or "wet" in lowered
        or "storm" in lowered
        or "showers" in lowered
    ):
        adjustments["degradation_multiplier"] = max(
            adjustments.get("degradation_multiplier", 1.0),
            1.25,
        )
        adjustments["safety_car_probability"] = max(
            adjustments.get("safety_car_probability", 0.0),
            0.55,
        )
        adjustments["base_lap_time_multiplier"] = 1.08
        adjustments["scenario_label"] = "wet_weather"

    # -------------------------
    # Push / aggressive driving
    # -------------------------
    if (
        "push" in lowered
        or "attack" in lowered
        or "aggressive" in lowered
        or "quali laps" in lowered
    ):
        adjustments["degradation_multiplier"] = max(
            adjustments.get("degradation_multiplier", 1.0),
            1.15,
        )
        adjustments["base_lap_time_multiplier"] = min(
            adjustments.get("base_lap_time_multiplier", 1.0),
            0.98,
        )
        adjustments["scenario_label"] = "aggressive_push"

    # -------------------------
    # Conservative management
    # -------------------------
    if (
        "manage tyres" in lowered
        or "conservative" in lowered
        or "save tyres" in lowered
        or "tyre saving" in lowered
    ):
        adjustments["degradation_multiplier"] = min(
            adjustments.get("degradation_multiplier", 1.0),
            0.85,
        )
        adjustments["base_lap_time_multiplier"] = max(
            adjustments.get("base_lap_time_multiplier", 1.0),
            1.01,
        )
        adjustments["scenario_label"] = "conservative_tyre_management"

    # -------------------------
    # Ferrari mode / pit chaos lol
    # -------------------------
    if (
        "ferrari" in lowered
        or "pit crew chaos" in lowered
        or "strategy disaster" in lowered
        or "clown" in lowered
    ):
        adjustments["pit_variance_multiplier"] = 4.0
        adjustments["pit_loss_multiplier"] = 1.15
        adjustments["scenario_label"] = "ferrari_mode"

    # -------------------------
    # Forced one-stop
    # -------------------------
    if (
        "one-stop" in lowered
        or "one stop" in lowered
        or "1-stop" in lowered
        or "1 stop" in lowered
    ):
        adjustments["max_stops"] = 1
        adjustments["scenario_label"] = "forced_one_stop"

    return adjustments