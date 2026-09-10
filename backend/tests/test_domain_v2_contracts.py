from datetime import datetime, timedelta, timezone, tzinfo
import math
import inspect
from typing import get_args, get_origin
import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain_v2.enums import (
    DistributionKind,
    ConfidenceLevel,
    StrategyActionType,
    TriggerMetric,
    TriggerOperator,
    TrackStatus,
    TyreCompound,
)
from app.domain_v2.estimates import (
    EmpiricalQuantiles,
    ModelVersion,
    PaceEstimate,
    RaceTimeDeltaEstimate,
    RejoinEstimate,
    ScenarioFrequency,
    StatisticalInterval,
    Uncertainty,
)
from app.domain_v2.identity import CompetitorId, EventId, SessionId
from app.domain_v2.provenance import ExternalIdentifier
from app.domain_v2.race_state import (
    CarState, Event, LapObservation, RaceState, Session,
    TrackStatusState, WeatherState,
)
from app.domain_v2.timing import Gap
from app.domain_v2.strategy import (
    DecisionTrigger,
    DecisionRecommendation,
    PositionProbability,
    StrategyAction,
    StrategyEvaluation,
    StrategyOption,
    StrategyPlan,
    MetricRef,
)
from app.domain_v2.tyre import TyreSet, TyreSetState
from app.domain_v2.validation import ValidationMetric, ValidationResult


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
OUR_COMPETITOR = CompetitorId("entry-5")


def state(**updates):
    values = {
        "session": Session(session_id=SessionId("race-1"), event=Event(event_id=EventId("event-1"), name="Test GP"), name="Race"),
        "observation_cutoff": NOW,
        "competitors": (CarState(competitor_id=CompetitorId("entry-5"), observed_at=NOW, current_lap=27),),
    }
    values.update(updates)
    return RaceState(**values)


def test_race_state_is_immutable_and_rejects_extras():
    snapshot = state()
    with pytest.raises(ValidationError):
        snapshot.observation_cutoff = NOW + timedelta(seconds=1)
    with pytest.raises(ValidationError):
        RaceState(**snapshot.model_dump(), openf1_session_key=123)


def test_provider_id_is_optional_metadata_not_domain_identity():
    assert state().session.external_ids == ()
    session = Session(
        session_id=SessionId("race-1"),
        event=Event(event_id=EventId("event-1"), name="Test GP"),
        name="Race",
        external_ids=(ExternalIdentifier(provider="openf1", resource_type="session", value="123"),),
    )
    assert str(session.session_id) == "race-1"


def test_multiple_provider_ids_do_not_change_canonical_identity_schema():
    first = Session(
        session_id=SessionId("race-1"),
        event=Event(event_id=EventId("event-1"), name="Test GP"),
        name="Race",
        external_ids=(ExternalIdentifier(provider="openf1", resource_type="session", value="123"),),
    )
    second = first.model_copy(
        update={"external_ids": first.external_ids + (
            ExternalIdentifier(provider="team_feed", resource_type="session", value="mel-2026-race"),
        )}
    )
    assert first.session_id == second.session_id
    assert type(first.session_id) is type(second.session_id)


@pytest.mark.parametrize("age", [-1, -50])
def test_impossible_tyre_ages_are_rejected(age):
    with pytest.raises(ValidationError):
        TyreSetState(compound=TyreCompound.MEDIUM, age_laps=age)


def test_new_tyre_set_cannot_have_prior_age():
    with pytest.raises(ValidationError):
        TyreSet(tyre_set_id="m1", compound=TyreCompound.MEDIUM, is_new=True, initial_age_laps=2)


def test_invalid_estimate_unit_is_rejected():
    with pytest.raises(ValidationError):
        PaceEstimate(
            value=90,
            unit="ms",
            model_version=ModelVersion(model_name="pace", version="1", config_hash="sha256:abc12345"),
        )


def test_uncertainty_requires_ordered_interval():
    with pytest.raises(ValidationError):
        StatisticalInterval(lower=2, upper=1, method="empirical")


def test_uncertainty_can_be_bounded_without_gaussian_standard_deviation():
    uncertainty = Uncertainty(
        kind=DistributionKind.BOUNDED,
        interval=StatisticalInterval(lower=1, upper=2, method="sensitivity envelope"),
    )
    assert uncertainty.standard_deviation is None


def test_empirical_p10_p50_p90_are_ordered():
    uncertainty = Uncertainty(
        kind=DistributionKind.QUANTILE,
        quantiles=EmpiricalQuantiles(p10=1, p50=2, p90=3, sample_count=100),
    )
    assert uncertainty.quantiles.p50 == 2
    with pytest.raises(ValidationError):
        EmpiricalQuantiles(p10=3, p50=2, p90=1, sample_count=100)


def test_scenario_frequency_is_descriptive_and_not_probability_named():
    frequency = ScenarioFrequency(frequency=0.25, matching_scenarios=25, total_scenarios=100)
    assert frequency.frequency == 0.25
    assert "probability" not in ScenarioFrequency.model_fields


def test_probabilities_are_bounded_and_distribution_sums_to_one():
    with pytest.raises(ValidationError):
        PositionProbability(position=5, probability=1.1)
    option = StrategyOption(
        option_id="hold",
        plan=StrategyPlan(
            competitor_id=OUR_COMPETITOR,
            actions=(StrategyAction(action_type=StrategyActionType.STAY_OUT),),
        ),
    )
    with pytest.raises(ValidationError):
        StrategyEvaluation(
            option=option,
            position_distribution=(PositionProbability(position=5, probability=0.4),),
        )


def test_strategy_action_rejects_contradictory_fields():
    with pytest.raises(ValidationError):
        StrategyAction(action_type=StrategyActionType.STAY_OUT, compound=TyreCompound.HARD)
    with pytest.raises(ValidationError):
        StrategyAction(action_type=StrategyActionType.PIT_TARGET)


def test_decision_trigger_has_closed_operator_vocabulary():
    trigger = DecisionTrigger(
        target_competitor_id=OUR_COMPETITOR,
        operand=MetricRef(metric=TriggerMetric.GAP_BEHIND_S, subject=CompetitorId("entry-5")),
        operator=TriggerOperator.GT,
        threshold=2.4,
        action=StrategyAction(action_type=StrategyActionType.PIT_NOW, compound=TyreCompound.HARD),
    )
    assert trigger.operator is TriggerOperator.GT
    with pytest.raises(ValidationError):
        DecisionTrigger(
            target_competitor_id=OUR_COMPETITOR,
            operand=MetricRef(metric=TriggerMetric.GAP_BEHIND_S),
            operator="approximately",
            threshold=2.4,
            action=StrategyAction(action_type=StrategyActionType.STAY_OUT),
        )


def test_decision_trigger_rejects_arbitrary_metric_name():
    with pytest.raises(ValidationError):
        MetricRef(metric="driver_is_feeling_lucky")


def test_relative_competitor_metric_validates_cleanly():
    ref = MetricRef(
        metric=TriggerMetric.INTERVAL_TO_COMPETITOR_S,
        subject=CompetitorId("entry-5"),
        relative_to=CompetitorId("entry-6"),
    )
    assert ref.relative_to == CompetitorId("entry-6")


@pytest.mark.parametrize("operand", [
    MetricRef(metric=TriggerMetric.PIT_LOSS_S),
    MetricRef(metric=TriggerMetric.RAIN_CROSSOVER_LAPS),
    MetricRef(metric=TriggerMetric.TRACK_STATUS),
])
def test_global_trigger_metrics_reject_competitor_references(operand):
    with pytest.raises(ValidationError):
        MetricRef(metric=operand.metric, subject=CompetitorId("entry-5"))


def test_subject_and_relative_trigger_rules_are_enforced():
    with pytest.raises(ValidationError):
        MetricRef(metric=TriggerMetric.DEGRADATION_S_PER_LAP)
    with pytest.raises(ValidationError):
        MetricRef(
            metric=TriggerMetric.REJOIN_MARGIN_S,
            subject=CompetitorId("entry-5"), relative_to=CompetitorId("entry-5"),
        )


@pytest.mark.parametrize("operator,threshold", [
    (TriggerOperator.GT, 3.14),
    (TriggerOperator.CHANGES_TO, "whatever"),
])
def test_track_status_trigger_rejects_incompatible_operator_or_threshold(operator, threshold):
    with pytest.raises(ValidationError):
        DecisionTrigger(
            target_competitor_id=OUR_COMPETITOR,
            operand=MetricRef(metric=TriggerMetric.TRACK_STATUS), operator=operator,
            threshold=threshold, action=StrategyAction(action_type=StrategyActionType.STAY_OUT),
        )


def test_track_status_trigger_accepts_typed_transition():
    trigger = DecisionTrigger(
        target_competitor_id=OUR_COMPETITOR,
        operand=MetricRef(metric=TriggerMetric.TRACK_STATUS),
        operator=TriggerOperator.CHANGES_TO, threshold=TrackStatus.VSC,
        action=StrategyAction(action_type=StrategyActionType.PIT_NOW),
    )
    assert trigger.threshold is TrackStatus.VSC


@pytest.mark.parametrize("threshold", ["2.5", True])
def test_numeric_trigger_rejects_string_and_bool(threshold):
    with pytest.raises(ValidationError):
        DecisionTrigger(
            target_competitor_id=OUR_COMPETITOR,
            operand=MetricRef(metric=TriggerMetric.PIT_LOSS_S), operator=TriggerOperator.GT,
            threshold=threshold, action=StrategyAction(action_type=StrategyActionType.STAY_OUT),
        )


def test_numeric_trigger_rejects_changes_to():
    with pytest.raises(ValidationError):
        DecisionTrigger(
            target_competitor_id=OUR_COMPETITOR,
            operand=MetricRef(metric=TriggerMetric.PIT_LOSS_S),
            operator=TriggerOperator.CHANGES_TO, threshold=2.5,
            action=StrategyAction(action_type=StrategyActionType.STAY_OUT),
        )


def test_future_observations_are_rejected_by_cutoff():
    car = CarState(
        competitor_id=CompetitorId("entry-5"),
        observed_at=NOW + timedelta(seconds=1),
        recent_laps=(LapObservation(lap_number=28, lap_time_s=90, completed_at=NOW + timedelta(seconds=1)),),
    )
    with pytest.raises(ValidationError):
        state(competitors=(car,))


def test_full_field_competitors_may_have_different_lap_context_at_same_cutoff():
    snapshot = state(
        competitors=(
            CarState(competitor_id=CompetitorId("entry-5"), observed_at=NOW, current_lap=27),
            CarState(competitor_id=CompetitorId("entry-6"), observed_at=NOW, current_lap=26),
        )
    )
    assert {item.current_lap for item in snapshot.competitors} == {26, 27}


def test_lap_completion_is_required_and_cannot_postdate_car_observation():
    with pytest.raises(ValidationError):
        LapObservation(lap_number=1, lap_time_s=90)
    with pytest.raises(ValidationError):
        CarState(
            competitor_id=CompetitorId("entry-5"), observed_at=NOW,
            recent_laps=(LapObservation(lap_number=27, lap_time_s=90, completed_at=NOW + timedelta(seconds=1)),),
        )


@pytest.mark.parametrize("field,value", [
    ("weather", WeatherState(observed_at=NOW + timedelta(seconds=1))),
    ("track_status", TrackStatusState(status=TrackStatus.GREEN, observed_at=NOW + timedelta(seconds=1))),
])
def test_timed_state_cannot_postdate_cutoff(field, value):
    with pytest.raises(ValidationError):
        state(**{field: value})


def test_canonical_timestamps_normalise_to_utc_and_reject_unusable_tzinfo():
    offset_time = datetime(2026, 1, 1, 11, tzinfo=timezone(timedelta(hours=11)))
    assert state(observation_cutoff=offset_time).observation_cutoff == NOW

    class UnusableTimezone(tzinfo):
        def utcoffset(self, dt):
            return None

    with pytest.raises(ValidationError):
        state(observation_cutoff=datetime(2026, 1, 1, tzinfo=UnusableTimezone()))


@pytest.mark.parametrize("payload", [
    {}, {"seconds": 1, "laps": 1}, {"seconds": -1}, {"laps": 0}, {"laps": 1.5},
])
def test_gap_rejects_invalid_representations(payload):
    with pytest.raises(ValidationError):
        Gap(**payload)


def test_gap_supports_seconds_and_lapped_competitor():
    assert Gap(seconds=2.4).seconds == 2.4
    lapped = CarState(
        competitor_id=CompetitorId("entry-20"), observed_at=NOW,
        current_lap=26, gap_to_leader=Gap(laps=1),
    )
    assert lapped.gap_to_leader.laps == 1


@pytest.mark.parametrize("payload", [
    {"laps": True}, {"laps": "1"}, {"laps": 1.0}, {"seconds": "2.4"},
])
def test_gap_rejects_transport_coercion(payload):
    with pytest.raises(ValidationError):
        Gap(**payload)


def test_rejoin_uses_shared_seconds_and_lap_gap_contract():
    version = ModelVersion(model_name="rejoin", version="1", config_hash="sha256:abc12345")
    seconds = RejoinEstimate(
        gap_ahead=Gap(seconds=2.4), gap_behind=Gap(seconds=1.2), model_version=version,
    )
    lapped = RejoinEstimate(gap_ahead=Gap(laps=1), model_version=version)
    assert seconds.gap_ahead.seconds == 2.4
    assert lapped.gap_ahead.laps == 1


def test_model_version_records_name_version_and_config_hash():
    version = ModelVersion(model_name="pace", version="2.1.0", config_hash="sha256:abc12345")
    assert version.config_hash == "sha256:abc12345"


def _evaluation(option_id: str) -> StrategyEvaluation:
    return StrategyEvaluation(
        option=StrategyOption(
            option_id=option_id,
            plan=StrategyPlan(
                competitor_id=OUR_COMPETITOR,
                actions=(StrategyAction(action_type=StrategyActionType.STAY_OUT),),
            ),
        )
    )


def test_recommendation_requires_unique_evaluations_and_matching_preference():
    recommendation = DecisionRecommendation(
        competitor_id=OUR_COMPETITOR,
        preferred_option_id="hold", evaluations=(_evaluation("hold"),), confidence=ConfidenceLevel.MEDIUM,
    )
    assert recommendation.evaluations[0].option.option_id == "hold"
    with pytest.raises(ValidationError):
        DecisionRecommendation(
            competitor_id=OUR_COMPETITOR, preferred_option_id="pit",
            evaluations=(_evaluation("hold"),), confidence=ConfidenceLevel.LOW,
        )


def test_strategy_plan_requires_competitor_and_recommendation_cannot_mix_targets():
    with pytest.raises(ValidationError):
        StrategyPlan(actions=(StrategyAction(action_type=StrategyActionType.STAY_OUT),))
    other = StrategyEvaluation(
        option=StrategyOption(
            option_id="other",
            plan=StrategyPlan(
                competitor_id=CompetitorId("entry-6"),
                actions=(StrategyAction(action_type=StrategyActionType.STAY_OUT),),
            ),
        )
    )
    with pytest.raises(ValidationError):
        DecisionRecommendation(
            competitor_id=OUR_COMPETITOR,
            preferred_option_id="hold",
            evaluations=(_evaluation("hold"), other),
            confidence=ConfidenceLevel.LOW,
        )


def test_recommendation_trigger_target_must_match_but_condition_may_be_relative():
    relative_condition = MetricRef(
        metric=TriggerMetric.INTERVAL_TO_COMPETITOR_S,
        subject=OUR_COMPETITOR,
        relative_to=CompetitorId("entry-6"),
    )
    matching = DecisionTrigger(
        target_competitor_id=OUR_COMPETITOR,
        operand=relative_condition,
        operator=TriggerOperator.GT,
        threshold=21.8,
        action=StrategyAction(action_type=StrategyActionType.PIT_NOW),
    )
    recommendation = DecisionRecommendation(
        competitor_id=OUR_COMPETITOR,
        preferred_option_id="hold",
        evaluations=(_evaluation("hold"),),
        confidence=ConfidenceLevel.MEDIUM,
        change_triggers=(matching,),
    )
    assert recommendation.change_triggers[0].operand.relative_to == CompetitorId("entry-6")
    with pytest.raises(ValidationError):
        DecisionRecommendation(
            competitor_id=OUR_COMPETITOR,
            preferred_option_id="hold",
            evaluations=(_evaluation("hold"),),
            confidence=ConfidenceLevel.MEDIUM,
            change_triggers=(matching.model_copy(update={"target_competitor_id": CompetitorId("entry-6")}),),
        )
    with pytest.raises(ValidationError):
        DecisionRecommendation(
            competitor_id=OUR_COMPETITOR, preferred_option_id="hold",
            evaluations=(_evaluation("hold"), _evaluation("hold")), confidence=ConfidenceLevel.LOW,
        )


def test_position_distribution_is_non_empty_unique_and_normalised():
    with pytest.raises(ValidationError):
        StrategyEvaluation(option=_evaluation("hold").option, finish_position_distribution=())
    with pytest.raises(ValidationError):
        StrategyEvaluation(
            option=_evaluation("hold").option,
            finish_position_distribution=(
                PositionProbability(position=5, probability=0.5),
                PositionProbability(position=5, probability=0.5),
            ),
        )


def test_expected_race_time_delta_requires_seconds():
    version = ModelVersion(model_name="strategy", version="1", config_hash="sha256:abc12345")
    StrategyEvaluation(
        option=_evaluation("hold").option,
        expected_race_time_delta=RaceTimeDeltaEstimate(value=-1.2, model_version=version),
    )
    with pytest.raises(ValidationError):
        RaceTimeDeltaEstimate(value=-1.2, unit="ms", model_version=version)


@pytest.mark.parametrize("factory", [
    lambda: PaceEstimate(
        value=math.nan, model_version=ModelVersion(model_name="pace", version="1", config_hash="sha256:abc12345")
    ),
    lambda: Gap(seconds=math.inf),
    lambda: LapObservation(lap_number=1, lap_time_s=-math.inf, completed_at=NOW),
    lambda: PositionProbability(position=1, probability=math.nan),
    lambda: EmpiricalQuantiles(p10=1, p50=2, p90=math.inf, sample_count=10),
])
def test_non_finite_domain_numbers_are_rejected(factory):
    with pytest.raises(ValidationError):
        factory()


def test_validation_result_has_typed_non_empty_metrics():
    result = ValidationResult(
        case_id="case-1",
        metrics=(ValidationMetric(name="lap_time_mae", value=0.4, unit="s", sample_count=20),),
        model_versions=(ModelVersion(model_name="pace", version="1", config_hash="sha256:abc12345"),),
    )
    assert result.metrics[0].unit == "s"
    with pytest.raises(ValidationError):
        ValidationResult(case_id="case-1", metrics=())


def test_interfaces_import_without_infrastructure_modules():
    import app.domain_v2.interfaces as interfaces

    assert interfaces.RaceDataSource
    assert not hasattr(interfaces, "ValidationEngine")


def test_foundation_contract_fields_do_not_expose_mutable_collections():
    import app.domain_v2.estimates as estimates
    import app.domain_v2.provenance as provenance
    import app.domain_v2.race_state as race_state
    import app.domain_v2.strategy as strategy
    import app.domain_v2.tyre as tyre
    import app.domain_v2.validation as validation

    modules = (estimates, provenance, race_state, strategy, tyre, validation)

    def contains_mutable(annotation) -> bool:
        origin = get_origin(annotation)
        if origin in {list, dict, set}:
            return True
        return any(contains_mutable(argument) for argument in get_args(annotation))

    for module in modules:
        for _, contract in inspect.getmembers(module, inspect.isclass):
            if hasattr(contract, "model_fields") and contract.__module__ == module.__name__:
                assert not any(
                    contains_mutable(field.annotation)
                    for field in contract.model_fields.values()
                ), contract.__name__


def test_no_domain_v2_module_imports_infrastructure():
    forbidden = {"fastapi", "httpx", "openai", "app.api", "app.data_sources", "app.config"}
    domain_dir = Path(__file__).parents[1] / "app" / "domain_v2"
    imported: set[str] = set()
    for module in domain_dir.glob("*.py"):
        tree = ast.parse(module.read_text(), filename=str(module))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module)
    assert not {
        name for name in imported
        if any(name == item or name.startswith(f"{item}.") for item in forbidden)
    }
