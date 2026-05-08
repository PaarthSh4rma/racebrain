from fastapi import APIRouter
from pydantic import BaseModel, field_validator
from typing import Literal
from app.data.track_profiles import get_track_profile
from app.simulation.monte_carlo import calculate_win_probabilities
from app.simulation.strategy_generator import generate_strategies
from app.simulation.strategy_engine import compare_strategies

router = APIRouter(prefix="/monte-carlo", tags=["Monte Carlo"])

Compound = Literal["soft", "medium", "hard"]
MAX_STRATEGIES = 10
MAX_SIMULATIONS = 200

class StintRequest(BaseModel):
    compound: Compound
    laps: int

    @field_validator("laps")
    def validate_laps(cls, value):
        if value <= 0:
            raise ValueError("laps must be greater than 0")
        if value > 100:
            raise ValueError("laps too large")
        return value


class MonteCarloCompareRequest(BaseModel):
    base_lap_time: float = 90.0
    pit_loss: float = 22.0
    simulations: int = 500
    lap_variance: float = 0.35
    pit_variance: float = 1.5
    strategies: list[list[StintRequest]]


class MonteCarloGenerateRequest(BaseModel):
    track: str = "monaco"
    total_laps: int = 50
    simulations: int = 300
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

@router.post("/compare")
def monte_carlo_compare_endpoint(request: MonteCarloCompareRequest):
    strategies = [
        [stint.model_dump() for stint in strategy]
        for strategy in request.strategies
    ]

    simulations = min(request.simulations, MAX_SIMULATIONS)

    for strategy in strategies:
        total = sum(stint["laps"] for stint in strategy)
        if total <= 0:
            raise ValueError("invalid strategy: total laps must be > 0")

    result = calculate_win_probabilities(
        strategies=strategies,
        base_lap_time=request.base_lap_time,
        pit_loss=request.pit_loss,
        simulations=simulations,
        lap_variance=request.lap_variance,
        pit_variance=request.pit_variance,
    )

    return {
        "total_evaluated": len(strategies),
        "simulations_per_strategy": simulations,
        **result,
    }


@router.post("/generate")
def monte_carlo_generate_endpoint(request: MonteCarloGenerateRequest):
    simulations = min(request.simulations, MAX_SIMULATIONS)
    profile = get_track_profile(request.track)

    base_lap_time = profile["base_lap_time"]
    pit_loss = profile["pit_loss"]
    degradation_multiplier = profile["degradation_multiplier"]
    safety_car_probability = profile["safety_car_probability"]
    all_strategies = generate_strategies(
        total_laps=request.total_laps,
        include_one_stop=request.include_one_stop,
        include_two_stop=request.include_two_stop,
    )

    deterministic_result = compare_strategies(
        base_lap_time=base_lap_time,
        pit_loss=pit_loss,
        strategies=all_strategies,
        degradation_multiplier=degradation_multiplier,
    )

    strategies = [
        item["strategy"]
        for item in deterministic_result["ranked_strategies"][:MAX_STRATEGIES]
    ]

    print(f"Generated {len(all_strategies)} strategies")
    print(f"Evaluating top {len(strategies)} deterministic candidates")
    print(f"Running {simulations} simulations each")

    result = calculate_win_probabilities(
        strategies=strategies,
        base_lap_time=base_lap_time,
        pit_loss=pit_loss,
        simulations=simulations,
        lap_variance=request.lap_variance,
        pit_variance=request.pit_variance,
        degradation_multiplier=degradation_multiplier,
        safety_car_probability=safety_car_probability,
    )

    return {
        "track": profile["name"],
        "base_lap_time": base_lap_time,
        "pit_loss": pit_loss,
        "degradation_multiplier": degradation_multiplier,
        "safety_car_probability": safety_car_probability,
        "total_generated": len(all_strategies),
        "deterministic_candidates_evaluated": len(strategies),
        "simulations_per_strategy": simulations,
        **result,
    }