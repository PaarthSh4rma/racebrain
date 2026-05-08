from fastapi import APIRouter
from pydantic import BaseModel, field_validator

from app.data.track_profiles import get_track_profile
from app.simulation.strategy_generator import generate_strategies
from app.simulation.strategy_engine import compare_strategies
from app.simulation.monte_carlo import calculate_win_probabilities

router = APIRouter(prefix="/race-engineer", tags=["Race Engineer"])

MAX_STRATEGIES = 10
MAX_SIMULATIONS = 200


class RaceEngineerBriefingRequest(BaseModel):
    track: str = "monaco"
    total_laps: int = 50
    simulations: int = 200
    lap_variance: float = 0.35
    pit_variance: float = 1.5
    include_one_stop: bool = True
    include_two_stop: bool = True

    @field_validator("total_laps")
    def validate_total_laps(cls, value):
        if value < 10:
            raise ValueError("total_laps must be at least 10")
        if value > 100:
            raise ValueError("total_laps too large")
        return value


def format_strategy(strategy: list[dict]) -> str:
    return " → ".join(
        f"{stint['compound'].title()} {stint['laps']} laps"
        for stint in strategy
    )


def build_risks(result: dict, profile: dict) -> list[str]:
    risks = []

    if result["confidence"] == "low":
        risks.append("Strategy confidence is low because the top options are very close.")

    if profile["safety_car_probability"] >= 0.25:
        risks.append("Safety car probability is meaningful, so pit timing has higher uncertainty.")

    if profile["degradation_multiplier"] >= 1.15:
        risks.append("Tyre degradation is high, so longer stints may fall off sharply.")

    if not risks:
        risks.append("No major strategic risks detected from the current simulation inputs.")

    return risks


@router.post("/briefing")
def race_engineer_briefing(request: RaceEngineerBriefingRequest):
    simulations = min(request.simulations, MAX_SIMULATIONS)

    profile = get_track_profile(request.track)

    all_strategies = generate_strategies(
        total_laps=request.total_laps,
        include_one_stop=request.include_one_stop,
        include_two_stop=request.include_two_stop,
    )

    deterministic_result = compare_strategies(
        base_lap_time=profile["base_lap_time"],
        pit_loss=profile["pit_loss"],
        strategies=all_strategies,
        degradation_multiplier=profile["degradation_multiplier"],
    )

    candidate_strategies = [
        item["strategy"]
        for item in deterministic_result["ranked_strategies"][:MAX_STRATEGIES]
    ]

    monte_carlo_result = calculate_win_probabilities(
        strategies=candidate_strategies,
        base_lap_time=profile["base_lap_time"],
        pit_loss=profile["pit_loss"],
        simulations=simulations,
        lap_variance=request.lap_variance,
        pit_variance=request.pit_variance,
        degradation_multiplier=profile["degradation_multiplier"],
        safety_car_probability=profile["safety_car_probability"],
    )

    best = monte_carlo_result["best_strategy"]

    return {
        "track": profile["name"],
        "recommendation": {
            "strategy_id": best["strategy_id"],
            "strategy": best["strategy"],
            "strategy_text": format_strategy(best["strategy"]),
            "win_percentage": best["win_percentage"],
            "confidence": monte_carlo_result["confidence"],
            "summary": monte_carlo_result["recommendation"],
        },
        "race_engineer_briefing": {
            "decision": f"Prefer Strategy {best['strategy_id']}",
            "reasoning": [
                f"Best simulated win rate: {best['win_percentage']}%",
                f"Average race time: {best['average_total_time']}s",
                f"Gap to second-best strategy: {monte_carlo_result['win_gap_to_second']}%",
                f"Safety car appeared in {monte_carlo_result['safety_car_simulations']} / {simulations} simulations",
            ],
            "risks": build_risks(monte_carlo_result, profile),
        },
        "tool_results": {
            "simulations": simulations,
            "total_generated_strategies": len(all_strategies),
            "candidates_evaluated": len(candidate_strategies),
            "track_profile": {
                "base_lap_time": profile["base_lap_time"],
                "pit_loss": profile["pit_loss"],
                "degradation_multiplier": profile["degradation_multiplier"],
                "safety_car_probability": profile["safety_car_probability"],
            },
            "ranked_strategies": monte_carlo_result["ranked_strategies"],
        },
    }
