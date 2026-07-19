from fastapi import APIRouter, HTTPException, Query

from app.data_sources.openf1_client import OpenF1Client, OpenF1Error
from app.services.race_state_builder import build_race_state

router = APIRouter(prefix="/race-data", tags=["Race Data"])

client = OpenF1Client()


def call_openf1(method, *args, **kwargs):
    try:
        return method(*args, **kwargs)
    except OpenF1Error as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/sessions")
def get_sessions(
    year: int | None = Query(default=None),
    country_name: str | None = Query(default=None),
    session_name: str | None = Query(default=None),
):
    return call_openf1(
        client.get_sessions,
        year=year,
        country_name=country_name,
        session_name=session_name,
    )


@router.get("/sessions/{session_key}/drivers")
def get_drivers(session_key: int):
    return call_openf1(client.get_drivers, session_key)


@router.get("/sessions/{session_key}/laps")
def get_laps(
    session_key: int,
    driver_number: int | None = Query(default=None),
):
    return call_openf1(
        client.get_laps,
        session_key=session_key,
        driver_number=driver_number,
    )


@router.get("/sessions/{session_key}/stints")
def get_stints(
    session_key: int,
    driver_number: int | None = Query(default=None),
):
    return call_openf1(
        client.get_stints,
        session_key=session_key,
        driver_number=driver_number,
    )


@router.get("/sessions/{session_key}/weather")
def get_weather(session_key: int):
    return call_openf1(client.get_weather, session_key)


@router.get("/sessions/{session_key}/race-control")
def get_race_control(session_key: int):
    return call_openf1(client.get_race_control, session_key)


@router.get("/sessions/{session_key}/race-state")
def get_race_state(
    session_key: int,
    driver_number: int | None = Query(default=None),
):
    return call_openf1(
        build_race_state,
        session_key=session_key,
        driver_number=driver_number,
    )
