import re


def parse_scenario_adjustments(question: str) -> dict:
    lowered = question.lower()

    adjustments = {}

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

    if (
        "one-stop" in lowered
        or "one stop" in lowered
        or "1-stop" in lowered
        or "1 stop" in lowered
    ):
        adjustments["max_stops"] = 1

    return adjustments