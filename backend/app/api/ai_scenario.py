from fastapi import APIRouter
from pydantic import BaseModel

from app.ai.scenario_parser import parse_scenario_adjustments
from app.ai.scenario_analysis import compare_results, build_scenario_summary
from app.ai.tools import run_strategy_simulation
from app.ai.scenario_analysis import (
    build_agent_steps,
    build_contingency,
    build_scenario_summary,
    compare_results,
)

router = APIRouter(prefix="/ai", tags=["AI"])


class ScenarioRequest(BaseModel):
    question: str
    track: str
    total_laps: int
    simulations: int = 200
    original_result: dict


@router.post("/scenario")
def run_scenario(request: ScenarioRequest):
    adjustments = parse_scenario_adjustments(request.question)

    if not adjustments:
        return {
    "summary": "I could not detect a simulation-changing scenario in that question.",
    "adjustments": {},
    "agent_steps": [
        "Received user scenario question.",
        "Attempted to parse simulation adjustments.",
        "No supported adjustment was detected.",
    ],
    "comparison": None,
    "contingency": [
        "Try asking about degradation, safety car probability, rain, one-stop strategy, aggressive push, or pit stop chaos."
    ],
}

    modified_result = run_strategy_simulation(
        track=request.track,
        total_laps=request.total_laps,
        simulations=request.simulations,
        adjustments=adjustments,
    )

    comparison = compare_results(
        original=request.original_result,
        modified=modified_result,
    )

    return {
    "summary": build_scenario_summary(comparison, adjustments),
    "adjustments": adjustments,
    "agent_steps": build_agent_steps(adjustments),
    "comparison": comparison,
    "contingency": build_contingency(comparison, adjustments),
    "modified_result": modified_result,
}