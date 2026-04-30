from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.simulate import router as simulate_router
from app.api.strategy import router as strategy_router
from app.api.monte_carlo import router as monte_carlo_router

app = FastAPI(
    title="RaceBrain API",
    description="F1 strategy simulation and pit wall intelligence engine.",
    version="0.1.0",
)

app.include_router(health_router)
app.include_router(simulate_router)
app.include_router(strategy_router)
app.include_router(monte_carlo_router)