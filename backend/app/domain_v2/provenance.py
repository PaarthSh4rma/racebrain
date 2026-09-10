"""Provenance and data-quality contracts."""

from datetime import datetime, timezone

from pydantic import Field, field_validator

from .base import FrozenDomainModel
from .enums import DataQualityLevel


class ExternalIdentifier(FrozenDomainModel):
    """Optional provider identity; never substitutes for domain identity."""

    provider: str = Field(min_length=1)
    resource_type: str = Field(min_length=1)
    value: str = Field(min_length=1)


class Provenance(FrozenDomainModel):
    source: str = Field(min_length=1)
    source_version: str | None = None
    observed_at: datetime | None = None
    retrieved_at: datetime | None = None
    external_ids: tuple[ExternalIdentifier, ...] = ()
    transformations: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()

    @field_validator("observed_at", "retrieved_at")
    @classmethod
    def timestamps_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is not None:
            if value.tzinfo is None or value.utcoffset() is None:
                raise ValueError("timestamps must be usable timezone-aware values")
            return value.astimezone(timezone.utc)
        return None


class DataQuality(FrozenDomainModel):
    level: DataQualityLevel = DataQualityLevel.UNKNOWN
    completeness: float | None = Field(default=None, ge=0.0, le=1.0)
    warnings: tuple[str, ...] = ()
    missing_fields: tuple[str, ...] = ()
