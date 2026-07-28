from copy import deepcopy
from datetime import datetime, timedelta, timezone


def build_case(
    *,
    safety_car: bool = False,
    rain: bool = False,
    incomplete: bool = False,
    multiple_stints: bool = True,
):
    start = datetime(2024, 5, 26, 13, 0, tzinfo=timezone.utc)
    laps = []
    current = start
    for lap_number in range(1, 13):
        duration = 90.0 + lap_number * 0.12
        laps.append(
            {
                "session_key": 9523,
                "driver_number": 1,
                "lap_number": lap_number,
                "lap_duration": None if incomplete and lap_number == 3 else duration,
                "date_start": current.isoformat(),
            }
        )
        current += timedelta(seconds=duration)

    stints = [
        {
            "session_key": 9523,
            "driver_number": 1,
            "stint_number": 1,
            "lap_start": 1,
            "lap_end": 6 if multiple_stints else 12,
            "compound": "MEDIUM",
            "tyre_age_at_start": 0,
        }
    ]
    if multiple_stints:
        stints.extend(
            [
                {
                    "session_key": 9523,
                    "driver_number": 1,
                    "stint_number": 2,
                    "lap_start": 7,
                    "lap_end": 10,
                    "compound": "HARD",
                    "tyre_age_at_start": 0,
                },
                {
                    "session_key": 9523,
                    "driver_number": 1,
                    "stint_number": 3,
                    "lap_start": 11,
                    "lap_end": 12,
                    "compound": "SOFT",
                    "tyre_age_at_start": 0,
                },
            ]
        )

    weather = []
    for minute in (2, 6, 12, 20):
        weather.append(
            {
                "date": (start + timedelta(minutes=minute)).isoformat(),
                "air_temperature": 22.0,
                "track_temperature": 34.0 - minute * 0.1,
                "humidity": 55.0 + minute,
                "wind_speed": 2.1,
                "rainfall": 1 if rain and minute >= 12 else 0,
            }
        )
    if incomplete:
        weather.append({"air_temperature": 21.0})

    race_control = [
        {
            "date": (start + timedelta(minutes=3)).isoformat(),
            "lap_number": 2,
            "category": "Flag",
            "message": "YELLOW FLAG",
        }
    ]
    if safety_car:
        race_control.append(
            {
                "date": (start + timedelta(minutes=10)).isoformat(),
                "lap_number": 7,
                "category": "SafetyCar",
                "message": "SAFETY CAR DEPLOYED",
            }
        )
    race_control.append(
        {
            "date": (start + timedelta(minutes=18)).isoformat(),
            "lap_number": 12,
            "category": "Flag",
            "message": "RED FLAG",
        }
    )

    return {
        "sessions": [
            {
                "session_key": 9523,
                "session_name": "Race",
                "session_type": "Race",
                "country_name": "Monaco",
                "circuit_short_name": "Monte Carlo",
                "location": "Monaco",
                "year": 2024,
                "date_start": start.isoformat(),
            }
        ],
        "drivers": [
            {
                "driver_number": 1,
                "broadcast_name": "M DRIVER",
                "full_name": "Mock Driver",
                "name_acronym": "MCK",
                "team_name": "Fixture Racing",
            }
        ],
        "laps": laps,
        "stints": stints,
        "weather": weather,
        "race_control": race_control,
    }


DRY_RACE = build_case()
SAFETY_CAR_RACE = build_case(safety_car=True)
CHANGING_WEATHER_RACE = build_case(rain=True)
INCOMPLETE_DATA_RACE = build_case(incomplete=True)
MULTIPLE_STINT_RACE = build_case(multiple_stints=True)


def clone_case(case):
    return deepcopy(case)
