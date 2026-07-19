from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.data.track_profiles import get_track_profile
from app.simulation.monte_carlo import calculate_win_probabilities
from app.simulation.strategy_engine import compare_strategies
from app.simulation.strategy_generator import generate_strategies

router = APIRouter(prefix="/monte-carlo", tags=["Monte Carlo"])

Compound = Literal["soft", "medium", "hard"]
MAX_STRATEGIES = 10
MAX_SIMULATIONS = 200


class StintRequest(BaseModel):
    compound: Compound
    laps: int = Field(ge=1, le=100)


class MonteCarloCompareRequest(BaseModel):
    base_lap_time: float = Field(default=90.0, ge=40, le=180)
    pit_loss: float = Field(default=22.0, ge=0, le=60)
    simulations: int = Field(default=200, ge=1, le=MAX_SIMULATIONS)
    lap_variance: float = Field(default=0.35, ge=0, le=10)
    pit_variance: float = Field(default=1.5, ge=0, le=20)
    seed: int | None = None
    strategies: list[list[StintRequest]] = Field(min_length=1, max_length=MAX_STRATEGIES)

    @model_validator(mode="after")
    def validate_strategies(self):
        if any(not strategy for strategy in self.strategies):
            raise ValueError("strategies cannot contain an empty strategy")
        return self


class MonteCarloGenerateRequest(BaseModel):
    track: str = "monaco"
    total_laps: int = Field(default=50, ge=16, le=100)
    simulations: int = Field(default=200, ge=1, le=MAX_SIMULATIONS)
    base_lap_time: float | None = Field(default=None, ge=40, le=180)
    pit_loss: float | None = Field(default=None, ge=0, le=60)
    lap_variance: float = Field(default=0.35, ge=0, le=10)
    pit_variance: float = Field(default=1.5, ge=0, le=20)
    seed: int | None = None
    include_one_stop: bool = True
    include_two_stop: bool = True

    @model_validator(mode="after")
    def validate_strategy_types(self):
        if not self.include_one_stop and not self.include_two_stop:
            raise ValueError("at least one strategy type must be enabled")
        return self


class StrategyResult(BaseModel):
    strategy_id: int
    strategy: list[StintRequest]
    win_probability: float
    win_percentage: float
    average_total_time: float
    best_case: float
    worst_case: float
    std_dev: float


class MonteCarloResultFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    seed: int | None
    best_strategy: StrategyResult
    confidence: Literal["low", "medium", "high"]
    win_gap_to_second: float
    recommendation: str
    safety_car_probability: float
    safety_car_simulations: int
    safety_car_rate: float
    ranked_strategies: list[StrategyResult]


class MonteCarloCompareResponse(MonteCarloResultFields):
    total_evaluated: int
    simulations_per_strategy: int


class MonteCarloGenerateResponse(MonteCarloResultFields):
    track: str
    track_id: str
    base_lap_time: float
    pit_loss: float
    degradation_multiplier: float
    total_generated: int
    deterministic_candidates_evaluated: int
    simulations_per_strategy: int


@router.post("/compare", response_model=MonteCarloCompareResponse)
def monte_carlo_compare_endpoint(request: MonteCarloCompareRequest):
    strategies = [[stint.model_dump() for stint in strategy] for strategy in request.strategies]
    result = calculate_win_probabilities(
        strategies=strategies,
        base_lap_time=request.base_lap_time,
        pit_loss=request.pit_loss,
        simulations=request.simulations,
        lap_variance=request.lap_variance,
        pit_variance=request.pit_variance,
        seed=request.seed,
    )
    return {
        "total_evaluated": len(strategies),
        "simulations_per_strategy": request.simulations,
        **result,
    }


@router.post("/generate", response_model=MonteCarloGenerateResponse)
def monte_carlo_generate_endpoint(request: MonteCarloGenerateRequest):
    track_id = request.track.lower()
    profile = get_track_profile(track_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Unsupported track: {request.track}")

    base_lap_time = request.base_lap_time if request.base_lap_time is not None else profile["base_lap_time"]
    pit_loss = request.pit_loss if request.pit_loss is not None else profile["pit_loss"]
    degradation_multiplier = profile["degradation_multiplier"]
    safety_car_probability = profile["safety_car_probability"]
    all_strategies = generate_strategies(
        total_laps=request.total_laps,
        include_one_stop=request.include_one_stop,
        include_two_stop=request.include_two_stop,
    )
    if not all_strategies:
        raise HTTPException(status_code=422, detail="No valid strategies could be generated")

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
    result = calculate_win_probabilities(
        strategies=strategies,
        base_lap_time=base_lap_time,
        pit_loss=pit_loss,
        simulations=request.simulations,
        lap_variance=request.lap_variance,
        pit_variance=request.pit_variance,
        degradation_multiplier=degradation_multiplier,
        safety_car_probability=safety_car_probability,
        seed=request.seed,
    )
    return {
        "track": profile["name"],
        "track_id": track_id,
        "base_lap_time": base_lap_time,
        "pit_loss": pit_loss,
        "degradation_multiplier": degradation_multiplier,
        "total_generated": len(all_strategies),
        "deterministic_candidates_evaluated": len(strategies),
        "simulations_per_strategy": request.simulations,
        **result,
    }
