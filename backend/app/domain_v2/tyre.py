"""Tyre inventory and observed tyre-state contracts."""

from pydantic import Field, model_validator

from .base import FrozenDomainModel
from .enums import TyreCompound
from .identity import TyreSetId
from .provenance import Provenance


class TyreSet(FrozenDomainModel):
    tyre_set_id: TyreSetId
    compound: TyreCompound
    is_new: bool | None = None
    initial_age_laps: int = Field(default=0, ge=0)
    is_available: bool | None = None
    is_fitted: bool | None = None
    provenance: tuple[Provenance, ...] = ()

    @model_validator(mode="after")
    def new_set_has_no_prior_age(self):
        if self.is_new is True and self.initial_age_laps != 0:
            raise ValueError("a new tyre set cannot have prior lap age")
        if self.is_fitted is True and self.is_available is False:
            raise ValueError("a fitted tyre set cannot be unavailable")
        return self


class TyreSetState(FrozenDomainModel):
    compound: TyreCompound
    age_laps: int = Field(ge=0)
    tyre_set_id: TyreSetId | None = None
    stint_number: int | None = Field(default=None, ge=1)
    provenance: tuple[Provenance, ...] = ()


class Stint(FrozenDomainModel):
    start_lap: int = Field(ge=1)
    end_lap: int | None = Field(default=None, ge=1)
    tyre: TyreSetState

    @model_validator(mode="after")
    def end_is_not_before_start(self):
        if self.end_lap is not None and self.end_lap < self.start_lap:
            raise ValueError("end_lap cannot be before start_lap")
        return self
