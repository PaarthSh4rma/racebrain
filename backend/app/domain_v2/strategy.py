"""Structured strategy, trigger, evaluation, and recommendation contracts."""

from typing import Any

from pydantic import Field, model_validator

from .base import FrozenDomainModel
from .enums import (
    ConfidenceLevel,
    RiskLevel,
    StrategyActionType,
    TriggerMetric,
    TriggerOperator,
    TyreCompound,
)
from .estimates import ModelEstimate, ModelVersion, RejoinEstimate
from .identity import CompetitorId, TyreSetId
from .provenance import Provenance


class StrategyAction(FrozenDomainModel):
    action_type: StrategyActionType
    target_lap: int | None = Field(default=None, ge=1)
    window_end_lap: int | None = Field(default=None, ge=1)
    compound: TyreCompound | None = None
    tyre_set_id: TyreSetId | None = None
    reconsider_after_laps: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def fields_match_action(self):
        pit_fields = (self.target_lap, self.window_end_lap, self.compound, self.tyre_set_id)
        if self.action_type == StrategyActionType.STAY_OUT and any(v is not None for v in pit_fields):
            raise ValueError("stay_out cannot specify pit or tyre fields")
        if self.action_type == StrategyActionType.PIT_NOW and (
            self.target_lap is not None or self.window_end_lap is not None
        ):
            raise ValueError("pit_now cannot specify a future lap or window")
        if self.action_type == StrategyActionType.PIT_TARGET:
            if self.target_lap is None:
                raise ValueError("pit_target requires target_lap")
            if self.window_end_lap is not None and self.window_end_lap < self.target_lap:
                raise ValueError("pit window cannot end before target_lap")
        if self.action_type == StrategyActionType.RECONSIDER:
            if self.reconsider_after_laps is None:
                raise ValueError("reconsider requires reconsider_after_laps")
            if any(v is not None for v in pit_fields):
                raise ValueError("reconsider cannot specify pit or tyre fields")
        elif self.reconsider_after_laps is not None:
            raise ValueError("reconsider_after_laps is valid only for reconsider")
        return self


class StrategyPlan(FrozenDomainModel):
    actions: tuple[StrategyAction, ...] = Field(min_length=1)


class StrategyOption(FrozenDomainModel):
    option_id: str = Field(min_length=1)
    plan: StrategyPlan
    label: str | None = None


class MetricRef(FrozenDomainModel):
    metric: TriggerMetric
    subject: CompetitorId | None = None
    relative_to: CompetitorId | None = None

    @model_validator(mode="after")
    def relative_metric_has_two_distinct_competitors(self):
        if self.metric == TriggerMetric.INTERVAL_TO_COMPETITOR_S:
            if self.subject is None or self.relative_to is None:
                raise ValueError("interval metric requires subject and relative_to")
            if self.subject == self.relative_to:
                raise ValueError("relative competitor must differ from subject")
        elif self.relative_to is not None:
            raise ValueError("relative_to is valid only for a relative competitor metric")
        return self


class DecisionTrigger(FrozenDomainModel):
    operand: MetricRef
    operator: TriggerOperator
    threshold: float | int | str | bool
    action: StrategyAction
    rationale: str | None = None


class PositionProbability(FrozenDomainModel):
    position: int = Field(ge=1)
    probability: float = Field(ge=0.0, le=1.0)


class StrategyEvaluation(FrozenDomainModel):
    option: StrategyOption
    expected_race_time_delta: ModelEstimate | None = None
    expected_position: float | None = Field(default=None, ge=1.0)
    position_distribution: tuple[PositionProbability, ...] | None = None
    time_distribution: tuple[float, ...] | None = None
    time_distribution_unit: str | None = Field(default=None, pattern=r"^s$")
    rejoin: RejoinEstimate | None = None
    traffic_risk: RiskLevel = RiskLevel.UNKNOWN
    tyre_life_risk: RiskLevel = RiskLevel.UNKNOWN
    weather_sensitivity: ModelEstimate | None = None
    safety_car_sensitivity: ModelEstimate | None = None
    warnings: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    model_versions: tuple[ModelVersion, ...] = ()
    provenance: tuple[Provenance, ...] = ()

    @model_validator(mode="after")
    def distribution_semantics_are_complete(self):
        if self.time_distribution is not None and self.time_distribution_unit is None:
            raise ValueError("time_distribution requires time_distribution_unit")
        if self.position_distribution is not None:
            total = sum(item.probability for item in self.position_distribution)
            if abs(total - 1.0) > 1e-6:
                raise ValueError("position probabilities must sum to 1")
        return self


class DecisionRecommendation(FrozenDomainModel):
    preferred_action: StrategyAction
    evaluated_alternatives: tuple[StrategyEvaluation, ...]
    confidence: ConfidenceLevel
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    change_triggers: tuple[DecisionTrigger, ...] = ()
    model_versions: tuple[ModelVersion, ...] = ()
    provenance: tuple[Provenance, ...] = ()
