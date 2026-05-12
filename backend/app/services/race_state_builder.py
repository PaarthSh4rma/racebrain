from statistics import mean

from app.data_sources.openf1_client import OpenF1Client

client = OpenF1Client()


def average(values: list[float]) -> float | None:
    clean = [value for value in values if value is not None]

    if not clean:
        return None

    return round(mean(clean), 2)


def get_weather_summary(weather: list[dict]) -> dict:
    if not weather:
        return {}

    return {
        "air_temperature_avg": average(
            [item.get("air_temperature") for item in weather]
        ),
        "track_temperature_avg": average(
            [item.get("track_temperature") for item in weather]
        ),
        "humidity_avg": average(
            [item.get("humidity") for item in weather]
        ),
        "wind_speed_avg": average(
            [item.get("wind_speed") for item in weather]
        ),
        "rainfall_detected": any(item.get("rainfall") for item in weather),
    }


def get_race_control_summary(events: list[dict]) -> dict:
    safety_events = [
        event
        for event in events
        if "SAFETY CAR" in str(event.get("message", "")).upper()
        or "VIRTUAL SAFETY CAR" in str(event.get("message", "")).upper()
    ]

    red_flags = [
        event
        for event in events
        if "RED FLAG" in str(event.get("message", "")).upper()
    ]

    return {
        "total_events": len(events),
        "safety_car_events": len(safety_events),
        "red_flag_events": len(red_flags),
        "notable_events": [
            event.get("message")
            for event in events[:8]
            if event.get("message")
        ],
    }


def get_driver_lap_summary(laps: list[dict]) -> dict:
    lap_durations = [
        lap.get("lap_duration")
        for lap in laps
        if lap.get("lap_duration") is not None
    ]

    if not lap_durations:
        return {
            "laps_completed": 0,
            "average_lap_time": None,
            "best_lap_time": None,
        }

    return {
        "laps_completed": len(lap_durations),
        "average_lap_time": round(mean(lap_durations), 3),
        "best_lap_time": round(min(lap_durations), 3),
    }


def build_race_state(
    session_key: int,
    driver_number: int | None = None,
) -> dict:
    session_weather = client.get_weather(session_key)
    race_control = client.get_race_control(session_key)
    drivers = client.get_drivers(session_key)

    laps = client.get_laps(
        session_key=session_key,
        driver_number=driver_number,
    )

    stints = client.get_stints(
        session_key=session_key,
        driver_number=driver_number,
    )

    return {
        "session_key": session_key,
        "driver_number": driver_number,
        "weather_summary": get_weather_summary(session_weather),
        "race_control_summary": get_race_control_summary(race_control),
        "driver_lap_summary": get_driver_lap_summary(laps),
        "stints": stints,
        "drivers": drivers[:20],
        "data_sources": {
            "weather_records": len(session_weather),
            "race_control_events": len(race_control),
            "lap_records": len(laps),
            "stint_records": len(stints),
            "driver_records": len(drivers),
        },
    }