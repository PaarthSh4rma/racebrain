from fastapi import APIRouter
from pydantic import BaseModel

from app.ai.analysis_tools import (
    aggression_analysis,
    compare_top_two,
    confidence_analysis,
    risk_analysis,
)
from app.ai.llm_client import generate_race_engineer_response

router = APIRouter(prefix="/ai", tags=["AI"])


class LLMExplainRequest(BaseModel):
    question: str
    simulation_result: dict


def route_analysis(question: str, result: dict):
    lowered = question.lower()

    if "confidence" in lowered:
        return confidence_analysis(result)

    if (
        "compare" in lowered
        or "second" in lowered
        or "alternative" in lowered
    ):
        return compare_top_two(result)

    if (
        "risk" in lowered
        or "safe" in lowered
        or "safest" in lowered
    ):
        return risk_analysis(result)

    if (
        "aggressive" in lowered
        or "attack" in lowered
    ):
        return aggression_analysis(result)

    return confidence_analysis(result)


@router.post("/llm-explain")
def llm_explain(request: LLMExplainRequest):
    analysis = route_analysis(
        request.question,
        request.simulation_result,
    )

    response = generate_race_engineer_response(
        question=request.question,
        simulation_result=request.simulation_result,
        analysis=analysis,
    )

    return {
        "response": response,
        "analysis_used": analysis["answer_type"],
    }