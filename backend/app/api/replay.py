from fastapi import APIRouter, HTTPException, Query
from pydantic import ValidationError

from app.data_sources.openf1_client import OpenF1Error
from app.models.replay import (
    AlternativeStrategyComparison,
    DecisionLapAvailability,
    DriverSummary,
    HistoricalSession,
    ReplayAssessment,
    ReplayRequest,
    ReplaySnapshot,
    StrategyRecommendation,
)
from app.services import replay_service

router = APIRouter(prefix="/replay", tags=["Historical Decision Replay"])


def _safe_call(method, *args, **kwargs):
    try:
        return method(*args, **kwargs)
    except replay_service.ReplayValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except OpenF1Error as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


def _tolerant_response(model, records, unique_field: str):
    parsed = []
    seen = set()
    for record in records:
        try:
            item = model.model_validate(record)
        except (ValidationError, TypeError):
            continue
        value = getattr(item, unique_field)
        if value in seen:
            continue
        seen.add(value)
        parsed.append(item)
    return parsed


@router.get("/sessions", response_model=list[HistoricalSession])
def list_historical_sessions(
    year: int | None = Query(default=None),
    country_name: str | None = Query(default=None),
):
    records = _safe_call(
        replay_service.client.get_sessions,
        year=year,
        country_name=country_name,
        session_name="Race",
    )
    return _tolerant_response(HistoricalSession, records, "session_key")


@router.get("/sessions/{session_key}/drivers", response_model=list[DriverSummary])
def list_session_drivers(session_key: int):
    records = _safe_call(replay_service.client.get_drivers, session_key)
    return _tolerant_response(DriverSummary, records, "driver_number")


@router.get(
    "/sessions/{session_key}/drivers/{driver_number}/decision-laps",
    response_model=DecisionLapAvailability,
)
def list_decision_laps(session_key: int, driver_number: int):
    laps = _safe_call(
        replay_service.available_decision_laps,
        session_key,
        driver_number,
    )
    if not laps:
        raise HTTPException(
            status_code=404,
            detail="No completed decision laps were found for this driver.",
        )
    return {"session_key": session_key, "driver_number": driver_number, "laps": laps}


@router.post("/snapshot", response_model=ReplaySnapshot)
def replay_snapshot(request: ReplayRequest):
    return _safe_call(replay_service.build_replay_snapshot, request)


@router.post("/recommendation", response_model=StrategyRecommendation)
def replay_recommendation(request: ReplayRequest):
    snapshot = _safe_call(replay_service.build_replay_snapshot, request)
    return replay_service.recommend_strategy(snapshot)


@router.post("/alternatives", response_model=list[AlternativeStrategyComparison])
def replay_alternatives(request: ReplayRequest):
    assessment = _safe_call(replay_service.build_replay_assessment, request)
    return assessment.alternatives


@router.post("/assessment", response_model=ReplayAssessment)
def replay_assessment(request: ReplayRequest):
    return _safe_call(replay_service.build_replay_assessment, request)
