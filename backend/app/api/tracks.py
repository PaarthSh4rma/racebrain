from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.data.track_profiles import TRACK_PROFILES, get_track_profile

router = APIRouter(prefix="/tracks", tags=["Tracks"])


class TrackProfileResponse(BaseModel):
    id: str
    name: str
    base_lap_time: float
    pit_loss: float
    degradation_multiplier: float
    safety_car_probability: float


class TrackListResponse(BaseModel):
    tracks: list[TrackProfileResponse]


@router.get("", response_model=TrackListResponse)
def list_tracks():
    return {
        "tracks": [
            {
                "id": track_id,
                **profile,
            }
            for track_id, profile in TRACK_PROFILES.items()
        ]
    }


@router.get("/{track_id}", response_model=TrackProfileResponse)
def get_track(track_id: str):
    normalized_id = track_id.lower()
    profile = get_track_profile(normalized_id)
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Unsupported track: {track_id}")
    return {
        "id": normalized_id,
        **profile,
    }
