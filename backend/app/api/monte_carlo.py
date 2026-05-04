from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal

from app.simulation.monte_carlo import compare_monte_carlo_strategies
from app.simulation.strategy_generator import generate_strategies
from app.simulation.strategy_engine import compare_strategies

router = APIRouter(prefix="/monte-carlo", tags=["Monte Carlo"])

Compound = Literal["soft", "medium", "hard"]
MAX_STRATEGIES = 10
MAX_SIMULATIONS = 50

class StintRequest(BaseModel):
    compound: Compound
    laps: int


class MonteCarloCompareRequest(BaseModel):
    base_lap_time: float = 90.0
    pit_loss: float = 22.0
    simulations: int = 500
    lap_variance: float = 0.35
    pit_variance: float = 1.5
    strategies: list[list[StintRequest]]


class MonteCarloGenerateRequest(BaseModel):
    total_laps: int = 50
    base_lap_time: float = 90.0
    pit_loss: float = 22.0
    simulations: int = 300
    lap_variance: float = 0.35
    pit_variance: float = 1.5
    include_one_stop: bool = True
    include_two_stop: bool = True


@router.post("/compare")
def monte_carlo_compare_endpoint(request: MonteCarloCompareRequest):
    strategies = [
        [stint.model_dump() for stint in strategy]
        for strategy in request.strategies
    ]

    return compare_monte_carlo_strategies(
        strategies=strategies,
        base_lap_time=request.base_lap_time,
        pit_loss=request.pit_loss,
        simulations=request.simulations,
        lap_variance=request.lap_variance,
        pit_variance=request.pit_variance,
    )


@router.post("/generate")
def monte_carlo_generate_endpoint(request: MonteCarloGenerateRequest):
    simulations = min(request.simulations, MAX_SIMULATIONS)

    all_strategies = generate_strategies(
        total_laps=request.total_laps,
        include_one_stop=request.include_one_stop,
        include_two_stop=request.include_two_stop,
    )

    deterministic_result = compare_strategies(
        base_lap_time=request.base_lap_time,
        pit_loss=request.pit_loss,
        strategies=all_strategies,
    )

    strategies = [
        item["strategy"]
        for item in deterministic_result["ranked_strategies"][:MAX_STRATEGIES]
    ]

    print(f"Generated {len(all_strategies)} strategies")
    print(f"Evaluating top {len(strategies)} deterministic candidates")
    print(f"Running {simulations} simulations each")

    result = compare_monte_carlo_strategies(
        strategies=strategies,
        base_lap_time=request.base_lap_time,
        pit_loss=request.pit_loss,
        simulations=simulations,
        lap_variance=request.lap_variance,
        pit_variance=request.pit_variance,
    )

    return {
        "total_generated": len(all_strategies),
        "deterministic_candidates_evaluated": len(strategies),
        "simulations_per_strategy": simulations,
        **result,
    }