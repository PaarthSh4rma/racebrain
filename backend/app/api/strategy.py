from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal

from app.simulation.strategy_engine import compare_strategies

router = APIRouter(prefix="/strategy", tags=["Strategy"])

Compound = Literal["soft", "medium", "hard"]


class StintRequest(BaseModel):
    compound: Compound
    laps: int


class StrategyCompareRequest(BaseModel):
    base_lap_time: float = 90.0
    pit_loss: float = 22.0
    strategies: list[list[StintRequest]]


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