"""Read-only discovery helpers for the historical RaceState workbench."""

from dataclasses import dataclass
from math import isfinite

from app.adapters.openf1_v2.dto import DriverDTO, LapDTO, MeetingDTO, SessionDTO
from app.adapters.openf1_v2.mapper import ReconstructionFailure
from app.data_sources.openf1_client import OpenF1Client


class HistoricalDiscoveryError(RuntimeError):
    """The provider returned a structurally unusable discovery payload."""


@dataclass(frozen=True)
class HistoricalSessionOption:
    session_key: int
    meeting_key: int
    year: int
    event_name: str
    country_name: str
    location: str
    session_name: str
    session_type: str | None


@dataclass(frozen=True)
class HistoricalDriverOption:
    driver_number: int
    full_name: str
    name_acronym: str | None
    team_name: str | None


def _parsed(raw, model):
    result = []
    for value in raw:
        try:
            result.append(model.model_validate(value))
        except (TypeError, ValueError):
            continue
    return result


def discover_race_sessions(year: int, client: OpenF1Client) -> tuple[HistoricalSessionOption, ...]:
    raw_sessions = client.get_sessions(year=year, session_name="Race")
    raw_meetings = client.get_meetings(year=year)
    if not isinstance(raw_sessions, list) or not isinstance(raw_meetings, list):
        raise HistoricalDiscoveryError("OpenF1 returned malformed historical session data.")
    sessions = _parsed(raw_sessions, SessionDTO)
    meetings = _parsed(raw_meetings, MeetingDTO)
    by_key = {meeting.meeting_key: meeting for meeting in meetings if meeting.meeting_key is not None}
    options = []
    for session in sessions:
        meeting = by_key.get(session.meeting_key)
        if (
            session.session_key is None
            or session.meeting_key is None
            or meeting is None
            or meeting.year != year
            or not meeting.meeting_name
            or not meeting.country_name
            or not meeting.location
            or not session.session_name
        ):
            continue
        options.append(HistoricalSessionOption(
            session_key=session.session_key,
            meeting_key=session.meeting_key,
            year=year,
            event_name=meeting.meeting_name,
            country_name=meeting.country_name,
            location=meeting.location,
            session_name=session.session_name,
            session_type=session.session_type,
        ))
    return tuple(sorted({item.session_key: item for item in options}.values(), key=lambda item: (item.event_name, item.session_key)))


def discover_session_drivers(session_key: int, client: OpenF1Client) -> tuple[HistoricalDriverOption, ...]:
    raw_drivers = client.get_drivers(session_key)
    if not isinstance(raw_drivers, list):
        raise HistoricalDiscoveryError("OpenF1 returned malformed historical driver data.")
    drivers = _parsed(raw_drivers, DriverDTO)
    options = []
    for driver in drivers:
        if driver.session_key not in {None, session_key} or driver.driver_number is None:
            continue
        name = driver.full_name or driver.broadcast_name or " ".join(filter(None, (driver.first_name, driver.last_name)))
        if not name:
            continue
        options.append(HistoricalDriverOption(driver.driver_number, name, driver.name_acronym, driver.team_name))
    return tuple(sorted({item.driver_number: item for item in options}.values(), key=lambda item: item.driver_number))


def discover_decision_laps(session_key: int, driver_number: int, client: OpenF1Client) -> tuple[int, ...]:
    drivers = discover_session_drivers(session_key, client)
    if driver_number not in {item.driver_number for item in drivers}:
        raise ReconstructionFailure("The focal driver is missing from session driver entries.")
    raw_laps = client.get_laps(session_key)
    if not isinstance(raw_laps, list):
        raise HistoricalDiscoveryError("OpenF1 returned malformed historical lap data.")
    laps = _parsed(raw_laps, LapDTO)
    usable = {
        lap.lap_number
        for lap in laps
        if lap.session_key in {None, session_key}
        and lap.driver_number == driver_number
        and lap.lap_number is not None
        and lap.lap_number > 0
        and lap.date_start is not None
        and lap.lap_duration is not None
        and isfinite(lap.lap_duration)
        and lap.lap_duration > 0
    }
    return tuple(sorted(usable))
