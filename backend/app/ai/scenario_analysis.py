def compare_results(original: dict, modified: dict):
    original_best = original["best_strategy"]
    modified_best = modified["best_strategy"]

    original_win = original_best["win_percentage"]
    new_win = modified_best["win_percentage"]

    return {
        "original_strategy": original_best["strategy_id"],
        "new_strategy": modified_best["strategy_id"],
        "original_win_rate": original_win,
        "new_win_rate": new_win,
        "win_rate_delta": round(new_win - original_win, 2),
        "strategy_changed": original_best["strategy_id"] != modified_best["strategy_id"],
        "original_confidence": original.get("confidence"),
        "new_confidence": modified.get("confidence"),
    }


def describe_adjustment(key: str, value):
    labels = {
        "degradation_multiplier": f"Tyre degradation adjusted to {value}x",
        "safety_car_probability": f"Safety car probability adjusted to {value}",
        "base_lap_time_multiplier": f"Base lap time adjusted by multiplier {value}",
        "pit_variance_multiplier": f"Pit variance adjusted by multiplier {value}",
        "pit_loss_multiplier": f"Pit loss adjusted by multiplier {value}",
        "max_stops": f"Strategy generation constrained to {value} stop(s)",
        "scenario_label": f"Semantic scenario detected: {value}",
    }

    return labels.get(key, f"{key} set to {value}")


def build_agent_steps(adjustments: dict):
    return [
        "Parsed user scenario into structured simulation adjustments.",
        *[describe_adjustment(key, value) for key, value in adjustments.items()],
        "Re-ran Monte Carlo strategy simulation with modified assumptions.",
        "Compared original recommendation against scenario-adjusted recommendation.",
        "Generated contingency guidance from the strategy delta.",
    ]


def build_scenario_summary(comparison: dict, adjustments: dict):
    if comparison["strategy_changed"]:
        return (
            f"The preferred strategy changed from Strategy {comparison['original_strategy']} "
            f"to Strategy {comparison['new_strategy']} after applying "
            f"{len(adjustments)} scenario adjustment(s)."
        )

    return (
        f"Strategy {comparison['new_strategy']} remains preferred after applying "
        f"{len(adjustments)} scenario adjustment(s)."
    )


def build_contingency(comparison: dict, adjustments: dict):
    notes = []

    if comparison["strategy_changed"]:
        notes.append(
            "Treat this as a meaningful scenario shift: the optimal call changes under the new assumptions."
        )
    else:
        notes.append(
            "The preferred strategy is robust to this scenario, but continue monitoring race conditions."
        )

    if "safety_car_probability" in adjustments:
        notes.append(
            "Keep pit timing flexible because safety car likelihood is now a key driver."
        )

    if "degradation_multiplier" in adjustments:
        notes.append(
            "Shorten stint flexibility windows and watch for tyre cliff behaviour."
        )

    if adjustments.get("max_stops") == 1:
        notes.append(
            "A forced one-stop should be treated as tyre-management heavy and vulnerable to late degradation."
        )

    if adjustments.get("scenario_label") == "wet_weather":
        notes.append(
            "Wet-weather assumptions increase volatility, so avoid locking into a strategy too early."
        )

    if adjustments.get("scenario_label") == "ferrari_mode":
        notes.append(
            "Pit execution risk is elevated. Avoid strategies that require precise stop timing."
        )

    return notes