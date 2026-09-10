"""Small, deterministic parsing helpers for inconsistent provider values."""

import re
from datetime import datetime, timezone
from math import isfinite
from typing import Any

from app.domain_v2.timing import Gap

_LAPPED = re.compile(r"^\+?\s*(\d+)\s+LAPS?$", re.IGNORECASE)


def empty_to_none(value: Any) -> Any:
    return None if isinstance(value, str) and not value.strip() else value


def utc_datetime(value: Any) -> datetime | None:
    value = empty_to_none(value)
    if value is None:
        return None
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None or parsed.utcoffset() is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def parse_gap(value: Any) -> Gap | None:
    value = empty_to_none(value)
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, str):
        match = _LAPPED.fullmatch(value.strip())
        if match:
            laps = int(match.group(1))
            return Gap(laps=laps) if laps > 0 else None
    try:
        seconds = float(value)
        return Gap(seconds=seconds) if isfinite(seconds) and seconds >= 0 else None
    except (TypeError, ValueError):
        return None
