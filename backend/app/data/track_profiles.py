from typing import Dict


TRACK_PROFILES: Dict[str, dict] = {
    "monaco": {
        "name": "Monaco",
        "base_lap_time": 74.5,
        "pit_loss": 20.5,
        "degradation_multiplier": 0.85,
        "safety_car_probability": 0.4,
    },
    "monza": {
        "name": "Monza",
        "base_lap_time": 80.0,
        "pit_loss": 24.0,
        "degradation_multiplier": 0.7,
        "safety_car_probability": 0.2,
    },
    "silverstone": {
        "name": "Silverstone",
        "base_lap_time": 88.0,
        "pit_loss": 21.5,
        "degradation_multiplier": 1.0,
        "safety_car_probability": 0.25,
    },
    "spa": {
        "name": "Spa",
        "base_lap_time": 104.0,
        "pit_loss": 23.0,
        "degradation_multiplier": 1.1,
        "safety_car_probability": 0.3,
    },
    "suzuka": {
        "name": "Suzuka",
        "base_lap_time": 91.0,
        "pit_loss": 22.5,
        "degradation_multiplier": 1.05,
        "safety_car_probability": 0.28,
    },
}


def get_track_profile(track: str) -> dict:
    key = track.lower()
    if key not in TRACK_PROFILES:
        raise ValueError(f"Track '{track}' not supported")

    return TRACK_PROFILES[key]