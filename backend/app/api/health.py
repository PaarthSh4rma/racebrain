from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    return {
        "status": "online",
        "service": "RaceBrain",
        "message": "Lights out and away we go."
    }