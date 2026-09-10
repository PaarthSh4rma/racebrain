"""Shared configuration for provider-independent V2 domain contracts."""

from pydantic import BaseModel, ConfigDict


class FrozenDomainModel(BaseModel):
    """Strict immutable value object used by decision-relevant contracts."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        allow_inf_nan=False,
        strict=True,
    )
