from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.simulate import router as simulate_router
from app.api.strategy import router as strategy_router
from app.api.monte_carlo import router as monte_carlo_router
from fastapi.middleware.cors import CORSMiddleware
from app.api.tracks import router as tracks_router
from app.api.race_engineer import router as race_engineer_router
from app.api.ai import router as ai_router
from app.api.ai_explain import router as ai_explain_router
from app.api.ai_llm import router as ai_llm_router
from app.api.ai_scenario import router as ai_scenario_router
app = FastAPI(
    title="RaceBrain API",
    description="F1 strategy simulation and pit wall intelligence engine.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router)
app.include_router(simulate_router)
app.include_router(strategy_router)
app.include_router(monte_carlo_router)
app.include_router(tracks_router)
app.include_router(race_engineer_router)
app.include_router(ai_router)
app.include_router(ai_explain_router)
app.include_router(ai_llm_router)
app.include_router(ai_scenario_router)