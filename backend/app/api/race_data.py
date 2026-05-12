from fastapi import APIRouter, Query

from app.data_sources.openf1_client import OpenF1Client

router = APIRouter(prefix="/race-data", tags=["Race Data"])

client = OpenF1Client()


@router.get("/sessions")
def get_sessions(
    year: int | None = Query(default=None),
    country_name: str | None = Query(default=None),
    session_name: str | None = Query(default=None),
):
    return client.get_sessions(
        year=year,
        country_name=country_name,
        session_name=session_name,
    )


@router.get("/sessions/{session_key}/drivers")
def get_drivers(session_key: int):
    return client.get_drivers(session_key)


@router.get("/sessions/{session_key}/laps")
def get_laps(
    session_key: int,
    driver_number: int | None = Query(default=None),
):
    return client.get_laps(
        session_key=session_key,
        driver_number=driver_number,
    )


@router.get("/sessions/{session_key}/stints")
def get_stints(
    session_key: int,
    driver_number: int | None = Query(default=None),
):
    return client.get_stints(
        session_key=session_key,
        driver_number=driver_number,
    )


@router.get("/sessions/{session_key}/weather")
def get_weather(session_key: int):
    return client.get_weather(session_key)


@router.get("/sessions/{session_key}/race-control")
def get_race_control(session_key: int):
    return client.get_race_control(session_key)