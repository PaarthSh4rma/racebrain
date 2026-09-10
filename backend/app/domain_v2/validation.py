"""Typed outputs for model validation; no validation algorithms live here."""

from pydantic import Field, model_validator

from .base import FrozenDomainModel
from .estimates import ModelVersion
from .provenance import Provenance


class ValidationMetric(FrozenDomainModel):
    name: str = Field(min_length=1)
    value: float
    unit: str = Field(min_length=1)
    sample_count: int | None = Field(default=None, ge=1)


class ValidationResult(FrozenDomainModel):
    case_id: str = Field(min_length=1)
    metrics: tuple[ValidationMetric, ...] = Field(min_length=1)
    warnings: tuple[str, ...] = ()
    model_versions: tuple[ModelVersion, ...] = ()
    provenance: tuple[Provenance, ...] = ()

    @model_validator(mode="after")
    def metric_names_are_unique(self):
        names = [metric.name for metric in self.metrics]
        if len(names) != len(set(names)):
            raise ValueError("validation metric names must be unique within a result")
        return self
