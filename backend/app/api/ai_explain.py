from fastapi import APIRouter
from pydantic import BaseModel
from app.ai.analysis_tools import (
    aggression_analysis,
    compare_top_two,
    confidence_analysis,
    risk_analysis,
)

router = APIRouter(prefix="/ai", tags=["AI"])


class ExplainRequest(BaseModel):
    message: str
    simulation_result: dict


def get_recommendation_type(win_gap: float, confidence: str) -> str:
    if confidence == "high" and win_gap >= 5:
        return "strong"
    if confidence == "medium" or win_gap >= 2:
        return "reasonable"
    return "marginal"


def get_risk_level(result: dict) -> str:
    risk_score = 0

    if result.get("confidence") == "low":
        risk_score += 2

    if result.get("win_gap_to_second", 0) < 2:
        risk_score += 2

    if result.get("safety_car_rate", 0) > 0.3:
        risk_score += 2

    if result.get("safety_car_rate", 0) > 0.5:
        risk_score += 1

    if risk_score >= 5:
        return "high"
    if risk_score >= 3:
        return "medium"
    return "low"


def build_key_factors(result: dict) -> list[str]:
    factors = []

    best = result["best_strategy"]

    factors.append(
        f"Strategy {best['strategy_id']} has the highest simulated win rate at {best['win_percentage']}%."
    )

    factors.append(
        f"The win gap to the second-best strategy is {result['win_gap_to_second']}%."
    )

    if result["confidence"] == "low":
        factors.append(
            "Model confidence is low, which means the top strategy is not clearly dominant."
        )

    if result["safety_car_rate"] > 0.25:
        factors.append(
            f"Safety car events appeared in {(result['safety_car_rate'] * 100):.0f}% of simulations."
        )

    factors.append(
        f"The model evaluated {result['simulations_per_strategy']} race runs per strategy."
    )

    return factors


def build_tradeoffs(result: dict) -> list[str]:
    ranked = result.get("ranked_strategies", [])

    if len(ranked) < 2:
        return ["Not enough ranked strategies available for tradeoff analysis."]

    best = ranked[0]
    second = ranked[1]

    return [
        f"Strategy {best['strategy_id']} has the best win rate, but Strategy {second['strategy_id']} is close behind at {second['win_percentage']}%.",
        "Because the top strategies are clustered, the call should stay flexible rather than locked in too early.",
        "A safety car or traffic change could easily flip the preferred option.",
    ]


def build_pit_wall_call(result: dict, risk_level: str, recommendation_type: str) -> str:
    best = result["best_strategy"]

    if recommendation_type == "strong":
        return (
            f"Commit to Strategy {best['strategy_id']} unless race conditions change sharply."
        )

    if risk_level == "high":
        return (
            f"Lean toward Strategy {best['strategy_id']}, but keep the pit window flexible. "
            "The model does not show a decisive advantage, so react to safety car timing and traffic."
        )

    return (
        f"Prefer Strategy {best['strategy_id']}, but continue monitoring the gap to the alternatives."
    )


@router.post("/explain")
def explain_strategy(request: ExplainRequest):
    result = request.simulation_result
    best = result["best_strategy"]
    message = request.message.lower()

    if "confidence" in message or "uncertain" in message:
        return {
            **confidence_analysis(result),
            "tools_used": ["confidence_analysis"],
        }

    if "compare" in message or "second" in message or "alternative" in message:
        return {
            **compare_top_two(result),
            "tools_used": ["strategy_comparison"],
        }

    if "risk" in message or "safe" in message or "safest" in message:
        return {
            **risk_analysis(result),
            "tools_used": ["risk_analysis"],
        }

    if "aggressive" in message or "attack" in message:
        return {
            **aggression_analysis(result),
            "tools_used": ["aggression_analysis"],
        }

    recommendation_type = get_recommendation_type(
        result["win_gap_to_second"],
        result["confidence"],
    )

    risk_level = get_risk_level(result)

    key_factors = build_key_factors(result)
    tradeoffs = build_tradeoffs(result)
    pit_wall_call = build_pit_wall_call(
        result,
        risk_level,
        recommendation_type,
    )

    return {
        "summary": (
            f"Strategy {best['strategy_id']} is preferred with a "
            f"{best['win_percentage']}% simulated win rate, but this is a "
            f"{recommendation_type} recommendation."
        ),
        "recommendation_type": recommendation_type,
        "risk_level": risk_level,
        "key_factors": key_factors,
        "tradeoffs": tradeoffs,
        "pit_wall_call": pit_wall_call,
        "follow_up_questions": [
            "Why is confidence low?",
            "Compare this with the second-best strategy.",
            "What would change the recommendation?",
        ],
        "tools_used": ["simulation_analysis"],
    }