from fastapi import APIRouter
from app.data.track_profiles import TRACK_PROFILES, get_track_profile

router = APIRouter(prefix="/tracks", tags=["Tracks"])


@router.get("")
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


@router.get("/{track_id}")
def get_track(track_id: str):
    profile = get_track_profile(track_id)
    return {
        "id": track_id.lower(),
        **profile,
    }