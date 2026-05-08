from fastapi import APIRouter
from pydantic import BaseModel

from app.ai.router import route_user_query

router = APIRouter(prefix="/ai", tags=["AI"])


class ChatRequest(BaseModel):
    message: str
    track: str = "monaco"
    total_laps: int = 50
    simulations: int = 200


@router.post("/chat")
def ai_chat(request: ChatRequest):
    return route_user_query(
        message=request.message,
        track=request.track,
        total_laps=request.total_laps,
        simulations=request.simulations,
    )