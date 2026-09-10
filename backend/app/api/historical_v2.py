"""Thin read-only API for the V2.1.5 historical workbench."""

import logging

from fastapi import APIRouter, HTTPException, Path, Query

from app.adapters.openf1_v2.mapper import ReconstructionFailure
from app.application_v2.historical_discovery import HistoricalDiscoveryError, discover_decision_laps, discover_race_sessions, discover_session_drivers
from app.application_v2.reconstruct_race_state import HistoricalRaceStateRequest, reconstruct_historical_race_state
from app.data_sources.openf1_client import OpenF1Client, OpenF1Error
from app.models.historical_v2 import DecisionLapSummary, HistoricalDriverSummary, HistoricalRaceStateApiRequest, HistoricalRaceStateResponse, HistoricalSessionSummary

router = APIRouter(prefix="/v2/historical", tags=["V2 Historical Race State"])
client = OpenF1Client()
logger = logging.getLogger("racebrain.historical_v2")

PROVIDER_UNAVAILABLE = "Historical data provider is temporarily unavailable."
SESSION_LOAD_FAILED = "Historical session data could not be loaded."
DRIVER_LOAD_FAILED = "Historical driver data could not be loaded."
LAP_LOAD_FAILED = "Historical decision-lap data could not be loaded."
RECONSTRUCTION_FAILED = "Historical race state could not be reconstructed."


def _failure(exc: ReconstructionFailure) -> HTTPException:
    message = str(exc)
    if "focal driver" in message:
        return HTTPException(status_code=404, detail=message)
    if "session metadata" in message.lower() or "OpenF1 meeting" in message:
        return HTTPException(status_code=502, detail="OpenF1 returned unusable historical session metadata.")
    return HTTPException(status_code=422, detail=message)


@router.get("/sessions", response_model=list[HistoricalSessionSummary])
def list_historical_sessions(year: int = Query(ge=2018, le=2100)):
    try:
        return discover_race_sessions(year, client)
    except OpenF1Error as exc:
        logger.warning("historical data provider unavailable during session discovery", exc_info=True)
        raise HTTPException(status_code=502, detail=PROVIDER_UNAVAILABLE) from exc
    except HistoricalDiscoveryError as exc:
        logger.warning("historical session discovery payload unusable", exc_info=True)
        raise HTTPException(status_code=502, detail=SESSION_LOAD_FAILED) from exc
    except Exception as exc:
        logger.exception("historical session discovery failed")
        raise HTTPException(status_code=500, detail="Historical session discovery failed safely.") from exc


@router.get("/sessions/{session_key}/drivers", response_model=list[HistoricalDriverSummary])
def list_historical_drivers(session_key: int = Path(gt=0)):
    try:
        return discover_session_drivers(session_key, client)
    except OpenF1Error as exc:
        logger.warning("historical data provider unavailable during driver discovery", exc_info=True)
        raise HTTPException(status_code=502, detail=PROVIDER_UNAVAILABLE) from exc
    except HistoricalDiscoveryError as exc:
        logger.warning("historical driver discovery payload unusable", exc_info=True)
        raise HTTPException(status_code=502, detail=DRIVER_LOAD_FAILED) from exc
    except Exception as exc:
        logger.exception("historical driver discovery failed")
        raise HTTPException(status_code=500, detail="Historical driver discovery failed safely.") from exc


@router.get("/sessions/{session_key}/drivers/{driver_number}/decision-laps", response_model=DecisionLapSummary)
def list_historical_decision_laps(session_key: int = Path(gt=0), driver_number: int = Path(gt=0)):
    try:
        laps = discover_decision_laps(session_key, driver_number, client)
        if not laps:
            raise HTTPException(status_code=404, detail="No defensible completed decision laps were found for this driver.")
        return DecisionLapSummary(session_key=session_key, driver_number=driver_number, laps=laps)
    except ReconstructionFailure as exc:
        raise _failure(exc) from exc
    except OpenF1Error as exc:
        logger.warning("historical data provider unavailable during lap discovery", exc_info=True)
        raise HTTPException(status_code=502, detail=PROVIDER_UNAVAILABLE) from exc
    except HistoricalDiscoveryError as exc:
        logger.warning("historical lap discovery payload unusable", exc_info=True)
        raise HTTPException(status_code=502, detail=LAP_LOAD_FAILED) from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("historical lap discovery failed")
        raise HTTPException(status_code=500, detail="Historical decision-lap discovery failed safely.") from exc


@router.post("/race-state", response_model=HistoricalRaceStateResponse)
def historical_race_state(request: HistoricalRaceStateApiRequest):
    try:
        result = reconstruct_historical_race_state(
            HistoricalRaceStateRequest(
                openf1_session_key=request.session_key,
                focal_driver_number=request.driver_number,
                decision_lap=request.decision_lap,
            ),
            client,
        )
        return HistoricalRaceStateResponse(race_state=result.race_state, diagnostics=result.diagnostics.__dict__)
    except ReconstructionFailure as exc:
        raise _failure(exc) from exc
    except OpenF1Error as exc:
        logger.warning("historical data provider unavailable during reconstruction", exc_info=True)
        raise HTTPException(status_code=502, detail=PROVIDER_UNAVAILABLE) from exc
    except Exception as exc:
        logger.exception("historical reconstruction failed")
        raise HTTPException(status_code=500, detail=RECONSTRUCTION_FAILED) from exc
