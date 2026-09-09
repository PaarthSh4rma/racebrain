"""Small inward-facing interfaces for interchangeable adapters and models."""

from datetime import datetime
from typing import Protocol, Sequence

from .estimates import DegradationEstimate, PaceEstimate
from .identity import CompetitorId, SessionId
from .race_state import CarState, RaceState
from .strategy import DecisionRecommendation, StrategyEvaluation, StrategyOption


class RaceDataSource(Protocol):
    """Reconstruct a canonical state without exposing provider payloads."""

    def race_state(self, session_id: SessionId, cutoff: datetime) -> RaceState: ...


class PaceModel(Protocol):
    """Estimate representative car pace from a bounded canonical state."""

    def estimate(self, state: RaceState, competitor_id: CompetitorId) -> PaceEstimate: ...


class TyreModel(Protocol):
    """Estimate tyre degradation from state and a specific car."""

    def estimate_degradation(self, state: RaceState, competitor_id: CompetitorId) -> DegradationEstimate: ...


class CompetitorModel(Protocol):
    """Return competitor states relevant to a focal car and decision horizon."""

    def relevant_competitors(
        self, state: RaceState, competitor_id: CompetitorId
    ) -> Sequence[CarState]: ...


class StrategySimulator(Protocol):
    """Evaluate structured options under explicit configuration and seed."""

    def evaluate(
        self, state: RaceState, options: Sequence[StrategyOption], *, seed: int
    ) -> Sequence[StrategyEvaluation]: ...


class DecisionEngine(Protocol):
    """Choose among supplied evaluations without natural-language generation."""

    def recommend(
        self, state: RaceState, evaluations: Sequence[StrategyEvaluation]
    ) -> DecisionRecommendation: ...


class ValidationEngine(Protocol):
    """Score model estimates against a separately supplied observed outcome."""

    def validate(self, case_id: str, estimate: StrategyEvaluation, observed: RaceState) -> dict[str, float]: ...
