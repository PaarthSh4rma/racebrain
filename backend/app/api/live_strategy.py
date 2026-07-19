from fastapi import APIRouter, HTTPException, Query
from app.data_sources.openf1_client import OpenF1Error

from app.services.race_state_builder import build_race_state
from app.services.live_strategy_service import generate_live_strategy_call

router = APIRouter(prefix="/live-strategy", tags=["Live Strategy"])


@router.get("/session/{session_key}")
def get_live_strategy_call(
    session_key: int,
    driver_number: int | None = Query(default=None),
):
    try:
        race_state = build_race_state(
            session_key=session_key,
            driver_number=driver_number,
        )
    except OpenF1Error as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    strategy_call = generate_live_strategy_call(race_state)

    return {
        "session_key": session_key,
        "driver_number": driver_number,
        "race_state_summary": {
            "weather": race_state["weather_summary"],
            "race_control": race_state["race_control_summary"],
            "driver_lap_summary": race_state["driver_lap_summary"],
        },
        "strategy_call": strategy_call,
    }
