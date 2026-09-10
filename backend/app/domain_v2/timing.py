"""Shared provider-independent timing values."""

from pydantic import Field, model_validator

from .base import FrozenDomainModel


class Gap(FrozenDomainModel):
    """Non-negative separation expressed in exactly one supported dimension."""

    seconds: float | None = Field(default=None, ge=0.0)
    laps: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def has_exactly_one_representation(self):
        if (self.seconds is None) == (self.laps is None):
            raise ValueError("gap requires exactly one of seconds or laps")
        return self
