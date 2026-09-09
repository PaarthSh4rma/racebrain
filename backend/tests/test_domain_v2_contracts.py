from datetime import datetime, timedelta, timezone
import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.domain_v2.enums import (
    DistributionKind,
    StrategyActionType,
    TriggerMetric,
    TriggerOperator,
    TyreCompound,
)
from app.domain_v2.estimates import (
    EmpiricalQuantiles,
    ModelVersion,
    PaceEstimate,
    ScenarioFrequency,
    StatisticalInterval,
    Uncertainty,
)
from app.domain_v2.identity import CompetitorId, EventId, SessionId
from app.domain_v2.provenance import ExternalIdentifier
from app.domain_v2.race_state import CarState, Event, LapObservation, RaceState, Session
from app.domain_v2.strategy import (
    DecisionTrigger,
    PositionProbability,
    StrategyAction,
    StrategyEvaluation,
    StrategyOption,
    StrategyPlan,
    MetricRef,
)
from app.domain_v2.tyre import TyreSet, TyreSetState


NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def state(**updates):
    values = {
        "session": Session(session_id=SessionId("race-1"), event=Event(event_id=EventId("event-1"), name="Test GP"), name="Race"),
        "session_lap": 27,
        "observation_cutoff": NOW,
        "competitors": (CarState(competitor_id=CompetitorId("entry-5"), current_lap=27),),
    }
    values.update(updates)
    return RaceState(**values)


def test_race_state_is_immutable_and_rejects_extras():
    snapshot = state()
    with pytest.raises(ValidationError):
        snapshot.session_lap = 28
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
    option = StrategyOption(option_id="hold", plan=StrategyPlan(actions=(StrategyAction(action_type="stay_out"),)))
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
        operand=MetricRef(metric=TriggerMetric.GAP_BEHIND_S, subject=CompetitorId("entry-5")),
        operator=TriggerOperator.GT,
        threshold=2.4,
        action=StrategyAction(action_type="pit_now", compound="hard"),
    )
    assert trigger.operator is TriggerOperator.GT
    with pytest.raises(ValidationError):
        DecisionTrigger(
            operand=MetricRef(metric=TriggerMetric.GAP_BEHIND_S),
            operator="approximately",
            threshold=2.4,
            action=StrategyAction(action_type="stay_out"),
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


def test_future_observations_are_rejected_by_cutoff():
    car = CarState(
        competitor_id=CompetitorId("entry-5"),
        recent_laps=(LapObservation(lap_number=28, lap_time_s=90, completed_at=NOW + timedelta(seconds=1)),),
    )
    with pytest.raises(ValidationError):
        state(competitors=(car,))


def test_full_field_competitors_may_have_different_lap_context_at_same_cutoff():
    snapshot = state(
        competitors=(
            CarState(competitor_id=CompetitorId("entry-5"), current_lap=27),
            CarState(competitor_id=CompetitorId("entry-6"), current_lap=26),
        )
    )
    assert {item.current_lap for item in snapshot.competitors} == {26, 27}


def test_model_version_records_name_version_and_config_hash():
    version = ModelVersion(model_name="pace", version="2.1.0", config_hash="sha256:abc12345")
    assert version.config_hash == "sha256:abc12345"


def test_interfaces_import_without_infrastructure_modules():
    import app.domain_v2.interfaces as interfaces

    assert interfaces.RaceDataSource


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
