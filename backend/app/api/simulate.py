from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal

from app.simulation.race_engine import simulate_race

router = APIRouter(prefix="/simulate", tags=["Simulation"])

Compound = Literal["soft", "medium", "hard"]


class StintRequest(BaseModel):
    compound: Compound
    laps: int


class SimulationRequest(BaseModel):
    base_lap_time: float = 90.0
    pit_loss: float = 22.0
    strategy: list[StintRequest]


@router.post("/race")
def simulate_race_endpoint(request: SimulationRequest):
    result = simulate_race(
        base_lap_time=request.base_lap_time,
        pit_loss=request.pit_loss,
        strategy=[stint.model_dump() for stint in request.strategy],
    )

    return result