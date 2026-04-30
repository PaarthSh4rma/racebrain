from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal

from app.simulation.strategy_engine import compare_strategies
from app.simulation.strategy_generator import generate_strategies

router = APIRouter(prefix="/strategy", tags=["Strategy"])

Compound = Literal["soft", "medium", "hard"]


class StintRequest(BaseModel):
    compound: Compound
    laps: int


class StrategyCompareRequest(BaseModel):
    base_lap_time: float = 90.0
    pit_loss: float = 22.0
    strategies: list[list[StintRequest]]


class StrategyGenerateRequest(BaseModel):
    total_laps: int = 50
    base_lap_time: float = 90.0
    pit_loss: float = 22.0
    include_one_stop: bool = True
    include_two_stop: bool = True


@router.post("/compare")
def compare_strategy_endpoint(request: StrategyCompareRequest):
    strategies = [
        [stint.model_dump() for stint in strategy]
        for strategy in request.strategies
    ]

    return compare_strategies(
        base_lap_time=request.base_lap_time,
        pit_loss=request.pit_loss,
        strategies=strategies,
    )


@router.post("/generate")
def generate_strategy_endpoint(request: StrategyGenerateRequest):
    strategies = generate_strategies(
        total_laps=request.total_laps,
        include_one_stop=request.include_one_stop,
        include_two_stop=request.include_two_stop,
    )

    result = compare_strategies(
        base_lap_time=request.base_lap_time,
        pit_loss=request.pit_loss,
        strategies=strategies,
    )

    return {
        "total_generated": len(strategies),
        **result,
    }