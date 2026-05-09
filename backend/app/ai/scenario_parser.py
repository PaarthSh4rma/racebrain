import re


def parse_scenario_adjustments(question: str) -> dict:
    lowered = question.lower()

    adjustments = {}

    deg_match = re.search(
        r"degradation.*?(\d+)%", lowered
    )

    if deg_match:
        percent = int(deg_match.group(1))
        adjustments["degradation_multiplier"] = 1 + (
            percent / 100
        )

    sc_drop_match = re.search(
        r"safety car.*?(drop|decrease|lower)",
        lowered,
    )

    if sc_drop_match:
        adjustments["safety_car_probability"] = 0.15

    sc_raise_match = re.search(
        r"safety car.*?(increase|higher|more)",
        lowered,
    )

    if sc_raise_match:
        adjustments["safety_car_probability"] = 0.5

    if "one-stop" in lowered or "one stop" in lowered:
        adjustments["max_stops"] = 1

    return adjustments