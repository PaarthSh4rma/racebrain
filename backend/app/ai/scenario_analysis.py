from app.ai.scenario_parser import (
    parse_scenario_adjustments,
)


def compare_results(original: dict, modified: dict):
    original_best = original["best_strategy"]
    modified_best = modified["best_strategy"]

    return {
        "original_strategy": original_best["strategy_id"],
        "new_strategy": modified_best["strategy_id"],
        "original_win_rate": original_best["win_percentage"],
        "new_win_rate": modified_best["win_percentage"],
        "strategy_changed": (
            original_best["strategy_id"]
            != modified_best["strategy_id"]
        ),
    }


def build_scenario_summary(
    comparison: dict,
    adjustments: dict,
):
    if comparison["strategy_changed"]:
        return (
            f"The preferred strategy changed from "
            f"Strategy {comparison['original_strategy']} "
            f"to Strategy {comparison['new_strategy']} "
            f"after modifying the simulation assumptions."
        )

    return (
        f"Strategy {comparison['new_strategy']} "
        f"remains preferred after the scenario adjustment."
    )