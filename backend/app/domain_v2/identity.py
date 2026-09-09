"""Opaque, RaceBrain-owned canonical identities.

The values identify domain concepts, not provider records. Adapters may derive a
stable value from a canonical natural identity, but provider IDs remain external
references and are never the semantic identity of these types.
"""

from pydantic import ConfigDict, Field, RootModel


class OpaqueId(RootModel[str]):
    model_config = ConfigDict(frozen=True)
    root: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")

    def __str__(self) -> str:
        return self.root


class EventId(OpaqueId):
    pass


class SessionId(OpaqueId):
    pass


class CompetitorId(OpaqueId):
    """Identity of a competitive session entry, never a physical chassis."""


class DriverId(OpaqueId):
    pass


class TyreSetId(OpaqueId):
    pass
