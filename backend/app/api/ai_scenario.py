from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.ai.scenario_analysis import (
    build_agent_steps,
    build_contingency,
    build_scenario_summary,
    compare_results,
)
from app.ai.scenario_parser import parse_scenario_adjustments
from app.ai.tools import run_strategy_simulation

router = APIRouter(prefix="/ai", tags=["AI"])


class ScenarioRequest(BaseModel):
    question: str = Field(min_length=1)
    track: str = Field(min_length=1)
    total_laps: int = Field(ge=16, le=100)
    simulations: int = Field(default=200, ge=1, le=200)
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
                "Try asking about degradation, safety car probability, rain, "
                "one-stop strategy, aggressive push, or pit stop chaos."
            ],
        }

    try:
        modified_result = run_strategy_simulation(
            track=request.track,
            total_laps=request.total_laps,
            simulations=request.simulations,
            adjustments=adjustments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

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
