"""Composable provider-shaped fixtures for V2.1 reconstruction tests."""


def historical_payload(session_key=999):
    return {
        "sessions": [{"session_key": session_key, "meeting_key": 88, "year": 2024, "country_name": "Monaco", "location": "Monte Carlo", "circuit_short_name": "Monaco", "session_name": "Race", "session_type": "Race", "irrelevant": "ignored"}],
        "meetings": [{"meeting_key": 88, "year": 2024, "meeting_name": "Monaco Grand Prix", "country_name": "Monaco", "location": "Monaco", "circuit_short_name": "Monte Carlo"}],
        "drivers": [
            {"session_key": session_key, "driver_number": 16, "full_name": "Charles Leclerc"},
            {"session_key": session_key, "driver_number": 4, "full_name": "Lando Norris"},
            {"session_key": session_key, "driver_number": 77, "full_name": "No Evidence"},
        ],
        "laps": [
            {"session_key": session_key, "driver_number": 16, "lap_number": 1, "date_start": "2024-05-26T13:00:00Z", "lap_duration": 60.0},
            {"session_key": session_key, "driver_number": 16, "lap_number": 2, "date_start": "2024-05-26T13:01:00Z", "lap_duration": 60.0},
            {"session_key": session_key, "driver_number": 4, "lap_number": 1, "date_start": "2024-05-26T13:00:02Z", "lap_duration": 61.0},
            {"session_key": session_key, "driver_number": 4, "lap_number": 2, "date_start": "2024-05-26T13:01:03Z", "lap_duration": 62.0},
            {"session_key": session_key, "driver_number": 4, "lap_number": 3, "date_start": "", "lap_duration": 62.0},
        ],
        "stints": [
            {"session_key": session_key, "driver_number": 16, "stint_number": 1, "lap_start": 1, "lap_end": 78, "compound": "MEDIUM", "tyre_age_at_start": 0},
            {"session_key": session_key, "driver_number": 4, "stint_number": 1, "lap_start": 1, "lap_end": 78, "compound": "HARD", "tyre_age_at_start": 1},
        ],
        "intervals": [
            {"session_key": session_key, "driver_number": 16, "date": "2024-05-26T13:01:59Z", "interval": None, "gap_to_leader": None},
            {"session_key": session_key, "driver_number": 4, "date": "2024-05-26T13:01:58Z", "interval": 1.25, "gap_to_leader": "+1 LAP"},
        ],
        "positions": [
            {"session_key": session_key, "driver_number": 16, "date": "2024-05-26T13:01:59Z", "position": 1},
            {"session_key": session_key, "driver_number": 4, "date": "2024-05-26T13:01:58Z", "position": 2},
        ],
        "pits": [{"session_key": session_key, "driver_number": 4, "date": "2024-05-26T13:00:50Z", "lap_number": 1, "lane_duration": 20.1}],
        "weather": [
            {"session_key": session_key, "date": "2024-05-26T13:01:30Z", "air_temperature": 22.0, "track_temperature": 34.0, "humidity": 60.0, "wind_speed": 2.5, "rainfall": 0},
            {"session_key": session_key, "date": "2024-05-26T13:03:00Z", "air_temperature": 5.0, "humidity": 99.0, "rainfall": 1},
        ],
        "race_control": [
            {"session_key": session_key, "date": "2024-05-26T13:00:10Z", "category": "SessionStatus", "message": "SESSION STARTED"},
            {"session_key": session_key, "date": "2024-05-26T13:03:00Z", "category": "SafetyCar", "scope": "Track", "message": "SAFETY CAR DEPLOYED"},
        ],
    }


class RecordingOpenF1Client:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []
        self.last_cache_hit = False

    def _take(self, name):
        self.calls.append(name)
        return self.payload[name]

    def get_sessions(self, **_): return self._take("sessions")
    def get_meetings(self, *_): return self._take("meetings")
    def get_drivers(self, *_): return self._take("drivers")
    def get_laps(self, *_): return self._take("laps")
    def get_stints(self, *_): return self._take("stints")
    def get_intervals(self, *_): return self._take("intervals")
    def get_position(self, *_): return self._take("positions")
    def get_pit(self, *_): return self._take("pits")
    def get_weather(self, *_): return self._take("weather")
    def get_race_control(self, *_): return self._take("race_control")
