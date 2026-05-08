from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/ai", tags=["AI"])


class ExplainRequest(BaseModel):
    message: str
    simulation_result: dict


@router.post("/explain")
def explain_strategy(request: ExplainRequest):
    result = request.simulation_result

    best = result["best_strategy"]

    response = (
        f"Strategy {best['strategy_id']} is currently preferred "
        f"with a {best['win_percentage']}% simulated win rate. "
        f"The model confidence is {result['confidence']}."
    )

    reasoning = []

    if result["win_gap_to_second"] < 2:
        reasoning.append(
            "The top strategies are very close together, so uncertainty is high."
        )

    if result["safety_car_rate"] > 0.25:
        reasoning.append(
            "Safety car probability is materially affecting the strategy outcomes."
        )

    reasoning.append(
        f"The simulation evaluated {result['simulations_per_strategy']} race runs per strategy."
    )

    return {
        "response": response,
        "reasoning": reasoning,
        "tools_used": [
            "simulation_analysis"
        ],
    }