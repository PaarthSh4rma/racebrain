"""Versioned, provider-independent canonical identity policy."""

from uuid import UUID, uuid5

from app.domain_v2.identity import CompetitorId, EventId, SessionId

RACEBRAIN_ID_NAMESPACE_V1 = UUID("ff3ca49a-3d53-5c5d-97c4-ec13f7b19ba7")


def canonicalize(*parts: object) -> str:
    return "|".join(" ".join(str(part).strip().lower().split()) for part in parts)


def _opaque(kind: str, natural_key: str) -> str:
    return f"{kind}:{uuid5(RACEBRAIN_ID_NAMESPACE_V1, f'v1|{kind}|{natural_key}')}"


def event_id(year: int, place: str, race_name: str) -> EventId:
    return EventId(_opaque("event", canonicalize("f1", year, place, race_name)))


def session_id(event: EventId, session_type: str, session_name: str) -> SessionId:
    return SessionId(_opaque("session", canonicalize(event, session_type, session_name)))


def competitor_id(session: SessionId, driver_number: int) -> CompetitorId:
    return CompetitorId(_opaque("competitor", canonicalize(session, driver_number)))
