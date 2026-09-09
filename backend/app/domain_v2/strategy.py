"""Structured strategy, trigger, evaluation, and recommendation contracts."""

from math import isfinite

from pydantic import Field, StrictFloat, StrictInt, model_validator

from .base import FrozenDomainModel
from .enums import (
    ConfidenceLevel,
    RiskLevel,
    StrategyActionType,
    TriggerMetric,
    TriggerOperator,
    TyreCompound,
    TrackStatus,
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
        subject_metrics = {
            TriggerMetric.GAP_AHEAD_S, TriggerMetric.GAP_BEHIND_S,
            TriggerMetric.DEGRADATION_S_PER_LAP,
            TriggerMetric.PACE_DELTA_S_PER_LAP, TriggerMetric.TYRE_AGE_LAPS,
        }
        relative_metrics = {
            TriggerMetric.INTERVAL_TO_COMPETITOR_S, TriggerMetric.REJOIN_MARGIN_S,
        }
        global_metrics = {
            TriggerMetric.PIT_LOSS_S, TriggerMetric.RAIN_CROSSOVER_LAPS,
            TriggerMetric.TRACK_STATUS,
        }
        if self.metric in relative_metrics:
            if self.subject is None or self.relative_to is None:
                raise ValueError("relative metric requires subject and relative_to")
            if self.subject == self.relative_to:
                raise ValueError("relative competitor must differ from subject")
        elif self.metric in subject_metrics:
            if self.subject is None:
                raise ValueError("metric requires a subject competitor")
            if self.relative_to is not None:
                raise ValueError("relative_to is valid only for a relative metric")
        elif self.metric in global_metrics and (self.subject is not None or self.relative_to is not None):
            raise ValueError("global metric cannot carry competitor references")
        return self


class DecisionTrigger(FrozenDomainModel):
    operand: MetricRef
    operator: TriggerOperator
    threshold: StrictFloat | StrictInt | TrackStatus
    action: StrategyAction
    rationale: str | None = None

    @model_validator(mode="after")
    def threshold_and_operator_match_metric(self):
        numeric_ops = {
            TriggerOperator.GT, TriggerOperator.GTE, TriggerOperator.LT,
            TriggerOperator.LTE, TriggerOperator.EQ, TriggerOperator.NE,
        }
        if self.operand.metric == TriggerMetric.TRACK_STATUS:
            if not isinstance(self.threshold, TrackStatus):
                raise ValueError("track-status threshold must be TrackStatus")
            if self.operator not in {TriggerOperator.EQ, TriggerOperator.NE, TriggerOperator.CHANGES_TO}:
                raise ValueError("operator is incompatible with track-status metric")
        else:
            if isinstance(self.threshold, bool) or not isinstance(self.threshold, (int, float)):
                raise ValueError("numeric metric threshold must be an int or float")
            if not isfinite(float(self.threshold)):
                raise ValueError("numeric metric threshold must be finite")
            if self.operator not in numeric_ops:
                raise ValueError("operator is incompatible with numeric metric")
        return self


class PositionProbability(FrozenDomainModel):
    position: int = Field(ge=1)
    probability: float = Field(ge=0.0, le=1.0)


class StrategyEvaluation(FrozenDomainModel):
    option: StrategyOption
    expected_race_time_delta: ModelEstimate | None = None
    expected_position: float | None = Field(default=None, ge=1.0)
    position_distribution: tuple[PositionProbability, ...] | None = Field(default=None, min_length=1)
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
        if self.position_distribution is not None:
            positions = [item.position for item in self.position_distribution]
            if len(positions) != len(set(positions)):
                raise ValueError("position distribution cannot repeat a position")
            total = sum(item.probability for item in self.position_distribution)
            if abs(total - 1.0) > 1e-6:
                raise ValueError("position probabilities must sum to 1")
        return self


class DecisionRecommendation(FrozenDomainModel):
    preferred_option_id: str = Field(min_length=1)
    evaluations: tuple[StrategyEvaluation, ...] = Field(min_length=1)
    confidence: ConfidenceLevel
    assumptions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    change_triggers: tuple[DecisionTrigger, ...] = ()
    model_versions: tuple[ModelVersion, ...] = ()
    provenance: tuple[Provenance, ...] = ()

    @model_validator(mode="after")
    def preferred_option_is_unique_and_evaluated(self):
        option_ids = [item.option.option_id for item in self.evaluations]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("evaluated StrategyOption IDs must be unique")
        if option_ids.count(self.preferred_option_id) != 1:
            raise ValueError("preferred_option_id must identify exactly one evaluation")
        return self
