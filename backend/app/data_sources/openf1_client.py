import httpx

OPENF1_BASE_URL = "https://api.openf1.org/v1"


class OpenF1Client:
    def __init__(self):
        self.base_url = OPENF1_BASE_URL

    def _get(self, endpoint: str, params: dict | None = None):
        url = f"{self.base_url}/{endpoint}"

        response = httpx.get(
            url,
            params=params or {},
            timeout=20,
        )

        response.raise_for_status()
        return response.json()

    def get_sessions(
        self,
        year: int | None = None,
        country_name: str | None = None,
        session_name: str | None = None,
    ):
        params = {}

        if year:
            params["year"] = year

        if country_name:
            params["country_name"] = country_name

        if session_name:
            params["session_name"] = session_name

        return self._get("sessions", params)

    def get_laps(self, session_key: int, driver_number: int | None = None):
        params = {"session_key": session_key}

        if driver_number:
            params["driver_number"] = driver_number

        return self._get("laps", params)

    def get_stints(self, session_key: int, driver_number: int | None = None):
        params = {"session_key": session_key}

        if driver_number:
            params["driver_number"] = driver_number

        return self._get("stints", params)

    def get_weather(self, session_key: int):
        return self._get("weather", {"session_key": session_key})

    def get_race_control(self, session_key: int):
        return self._get("race_control", {"session_key": session_key})

    def get_drivers(self, session_key: int):
        return self._get("drivers", {"session_key": session_key})