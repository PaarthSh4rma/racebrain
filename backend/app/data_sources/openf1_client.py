import logging
import time
from collections import OrderedDict
from copy import deepcopy
from dataclasses import dataclass
from threading import Lock, local
from typing import Any

import httpx

OPENF1_BASE_URL = "https://api.openf1.org/v1"
logger = logging.getLogger("racebrain.openf1")


class OpenF1Error(RuntimeError):
    """Safe application-level error for unavailable upstream race data."""


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class MemoryTTLCache:
    def __init__(self, max_size: int = 128):
        self.max_size = max_size
        self._items: OrderedDict[tuple, CacheEntry] = OrderedDict()
        self._lock = Lock()

    def get(self, key: tuple):
        with self._lock:
            entry = self._items.get(key)
            if entry is None:
                return None
            if entry.expires_at <= time.monotonic():
                self._items.pop(key, None)
                return None
            self._items.move_to_end(key)
            return deepcopy(entry.value)

    def set(self, key: tuple, value: Any, ttl: int):
        with self._lock:
            self._items[key] = CacheEntry(
                value=deepcopy(value),
                expires_at=time.monotonic() + ttl,
            )
            self._items.move_to_end(key)
            while len(self._items) > self.max_size:
                self._items.popitem(last=False)

    def clear(self):
        with self._lock:
            self._items.clear()


class OpenF1Client:
    TTL_BY_ENDPOINT = {
        "sessions": 900,
        "drivers": 900,
        "laps": 300,
        "stints": 300,
        "weather": 180,
        "race_control": 180,
    }

    def __init__(self, max_cache_size: int = 128, retries: int = 2):
        self.base_url = OPENF1_BASE_URL
        self.cache = MemoryTTLCache(max_size=max_cache_size)
        self.retries = retries
        self._request_state = local()
        self.last_cache_hit = False

    @property
    def last_cache_hit(self) -> bool:
        return getattr(self._request_state, "last_cache_hit", False)

    @last_cache_hit.setter
    def last_cache_hit(self, value: bool):
        self._request_state.last_cache_hit = value

    def clear_cache(self):
        self.cache.clear()

    @staticmethod
    def _cache_key(endpoint: str, params: dict) -> tuple:
        return endpoint, tuple(sorted((key, str(value)) for key, value in params.items()))

    def _get(
        self,
        endpoint: str,
        params: dict | None = None,
        *,
        bypass_cache: bool = False,
    ):
        request_params = params or {}
        url = f"{self.base_url}/{endpoint}"
        cache_key = self._cache_key(endpoint, request_params)
        self.last_cache_hit = False

        if not bypass_cache:
            cached = self.cache.get(cache_key)
            if cached is not None:
                self.last_cache_hit = True
                logger.info("openf1_cache", extra={"endpoint": endpoint, "cache_hit": True})
                return cached

        logger.info("openf1_cache", extra={"endpoint": endpoint, "cache_hit": False})
        started = time.monotonic()

        for attempt in range(self.retries + 1):
            try:
                response = httpx.get(url, params=request_params, timeout=20)
                response.raise_for_status()
                payload = response.json()
                self.cache.set(
                    cache_key,
                    payload,
                    ttl=self.TTL_BY_ENDPOINT.get(endpoint, 300),
                )
                logger.info(
                    "openf1_request",
                    extra={
                        "endpoint": endpoint,
                        "duration_ms": round((time.monotonic() - started) * 1000, 2),
                        "attempt": attempt + 1,
                    },
                )
                return payload
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status < 500 and status != 429:
                    break
                if attempt >= self.retries:
                    break
            except (httpx.TransportError, ValueError):
                if attempt >= self.retries:
                    break
            time.sleep(0.1 * (2**attempt))

        logger.warning(
            "openf1_failure",
            extra={
                "endpoint": endpoint,
                "duration_ms": round((time.monotonic() - started) * 1000, 2),
            },
        )
        raise OpenF1Error("OpenF1 race data is temporarily unavailable.")

    def get_sessions(
        self,
        year: int | None = None,
        country_name: str | None = None,
        session_name: str | None = None,
        session_key: int | None = None,
        *,
        bypass_cache: bool = False,
    ):
        params = {}
        if year:
            params["year"] = year
        if country_name:
            params["country_name"] = country_name
        if session_name:
            params["session_name"] = session_name
        if session_key:
            params["session_key"] = session_key
        return self._get("sessions", params, bypass_cache=bypass_cache)

    def get_laps(
        self,
        session_key: int,
        driver_number: int | None = None,
        *,
        bypass_cache: bool = False,
    ):
        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        return self._get("laps", params, bypass_cache=bypass_cache)

    def get_stints(
        self,
        session_key: int,
        driver_number: int | None = None,
        *,
        bypass_cache: bool = False,
    ):
        params = {"session_key": session_key}
        if driver_number:
            params["driver_number"] = driver_number
        return self._get("stints", params, bypass_cache=bypass_cache)

    def get_weather(self, session_key: int, *, bypass_cache: bool = False):
        return self._get(
            "weather",
            {"session_key": session_key},
            bypass_cache=bypass_cache,
        )

    def get_race_control(self, session_key: int, *, bypass_cache: bool = False):
        return self._get(
            "race_control",
            {"session_key": session_key},
            bypass_cache=bypass_cache,
        )

    def get_drivers(self, session_key: int, *, bypass_cache: bool = False):
        return self._get(
            "drivers",
            {"session_key": session_key},
            bypass_cache=bypass_cache,
        )
