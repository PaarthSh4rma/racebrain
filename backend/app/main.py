from fastapi import FastAPI
from app.api.health import router as health_router

app = FastAPI(
    title="RaceBrain API",
    description="F1 strategy simulation and pit wall intelligence engine.",
    version="0.1.0",
)

app.include_router(health_router)