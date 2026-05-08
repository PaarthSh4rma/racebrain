from fastapi import APIRouter
from pydantic import BaseModel

from app.ai.router import route_user_query

router = APIRouter(prefix="/ai", tags=["AI"])


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def ai_chat(request: ChatRequest):
    return route_user_query(request.message)