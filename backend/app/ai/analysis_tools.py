def get_top_strategies(result: dict, limit: int = 3) -> list[dict]:
    return result.get("ranked_strategies", [])[:limit]


def format_strategy(strategy: list[dict]) -> str:
    return " → ".join(
        f"{stint['compound'].title()} {stint['laps']} laps"
        for stint in strategy
    )


def confidence_analysis(result: dict) -> dict:
    gap = result.get("win_gap_to_second", 0)
    confidence = result.get("confidence", "unknown")
    safety_car_rate = result.get("safety_car_rate", 0)

    reasons = []

    if gap < 2:
        reasons.append(
            f"The win gap to second-best is only {gap}%, so the model does not have a clear winner."
        )

    if safety_car_rate > 0.25:
        reasons.append(
            f"Safety cars appeared in {(safety_car_rate * 100):.0f}% of simulations, increasing uncertainty."
        )

    if confidence == "low":
        reasons.append(
            "Multiple strategies are producing similar outcomes, so small race events can flip the recommendation."
        )

    return {
        "answer_type": "confidence_analysis",
        "summary": f"Confidence is {confidence} because the preferred strategy is not clearly separated from alternatives.",
        "points": reasons,
    }


def compare_top_two(result: dict) -> dict:
    strategies = get_top_strategies(result, 2)

    if len(strategies) < 2:
        return {
            "answer_type": "strategy_comparison",
            "summary": "There are not enough strategies to compare.",
            "points": [],
        }

    first, second = strategies[0], strategies[1]

    return {
        "answer_type": "strategy_comparison",
        "summary": (
            f"Strategy {first['strategy_id']} is preferred over Strategy {second['strategy_id']}, "
            f"but the gap is narrow."
        ),
        "points": [
            f"Strategy {first['strategy_id']}: {format_strategy(first['strategy'])}, {first['win_percentage']}% win rate.",
            f"Strategy {second['strategy_id']}: {format_strategy(second['strategy'])}, {second['win_percentage']}% win rate.",
            f"Gap: {first['win_percentage'] - second['win_percentage']:.1f} percentage points.",
            "Because the gap is small, the second strategy remains viable if traffic, tyre degradation, or safety car timing changes.",
        ],
    }


def risk_analysis(result: dict) -> dict:
    strategies = get_top_strategies(result, 5)

    if not strategies:
        return {
            "answer_type": "risk_analysis",
            "summary": "No strategies available for risk analysis.",
            "points": [],
        }

    safest = min(strategies, key=lambda s: s.get("std_dev", 999))

    return {
        "answer_type": "risk_analysis",
        "summary": f"Strategy {safest['strategy_id']} appears to be the lowest-variance option among the top candidates.",
        "points": [
            f"Lowest standard deviation among top candidates: {safest.get('std_dev')}s.",
            f"Strategy: {format_strategy(safest['strategy'])}.",
            "Lower variance usually means the strategy is less exposed to extreme race outcomes.",
            "This may not maximise win probability, but it can be safer when confidence is low.",
        ],
    }


def aggression_analysis(result: dict) -> dict:
    strategies = get_top_strategies(result, 5)

    aggressive = None

    for strategy in strategies:
      compounds = [stint["compound"].lower() for stint in strategy["strategy"]]
      soft_count = compounds.count("soft")

      score = soft_count * 2 + len(strategy["strategy"])

      if aggressive is None or score > aggressive["score"]:
          aggressive = {
              "score": score,
              "strategy": strategy,
          }

    selected = aggressive["strategy"]

    return {
        "answer_type": "aggression_analysis",
        "summary": f"Strategy {selected['strategy_id']} looks like the most aggressive top option.",
        "points": [
            f"Strategy: {format_strategy(selected['strategy'])}.",
            "It uses softer compounds and more attacking stint profiles.",
            "This can improve peak pace, but increases exposure to degradation and timing risk.",
        ],
    }