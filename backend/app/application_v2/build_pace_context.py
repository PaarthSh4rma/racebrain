"""Application service for cutoff-safe full-field modelling history."""

from dataclasses import dataclass

from app.adapters.openf1_v2.dto import IntervalDTO, LapDTO, PitDTO, PositionDTO, RaceControlDTO, StintDTO, WeatherDTO
from app.adapters.openf1_v2.mapper import OpenF1Dataset, ParsedRecords, ReconstructionDiagnostics
from app.adapters.openf1_v2.modelling_history import ModellingHistoryDiagnostics, build_pace_context
from app.application_v2.reconstruct_race_state import (
    HistoricalRaceStateRequest,
    _parse,
    reconstruct_historical_race_state,
)
from app.data_sources.openf1_client import OpenF1Client
from app.domain_v2.modelling import PaceEstimationContext


@dataclass(frozen=True)
class HistoricalPaceContextResult:
    context: PaceEstimationContext
    diagnostics: ModellingHistoryDiagnostics
    reconstruction_diagnostics: ReconstructionDiagnostics
    modelling_feed_cache_hits: dict[str, bool]


def build_historical_pace_context(
    request: HistoricalRaceStateRequest,
    client: OpenF1Client | None = None,
) -> HistoricalPaceContextResult:
    """Reconstruct canonical state, then build longer history at its exact cutoff."""

    client = client or OpenF1Client()
    reconstruction = reconstruct_historical_race_state(request, client)
    key = request.openf1_session_key
    specs = (
        ("laps", LapDTO, lambda: client.get_laps(key)),
        ("stints", StintDTO, lambda: client.get_stints(key)),
        ("intervals", IntervalDTO, lambda: client.get_intervals(key)),
        ("positions", PositionDTO, lambda: client.get_position(key)),
        ("pits", PitDTO, lambda: client.get_pit(key)),
        ("weather", WeatherDTO, lambda: client.get_weather(key)),
        ("race_control", RaceControlDTO, lambda: client.get_race_control(key)),
    )
    parsed = {}
    cache_hits = {}
    for name, model, fetch in specs:
        parsed[name] = _parse(fetch(), model)
        cache_hits[name] = client.last_cache_hit
    empty = ParsedRecords(())
    dataset = OpenF1Dataset(
        sessions=empty,
        meetings=empty,
        drivers=empty,
        laps=parsed["laps"],
        stints=parsed["stints"],
        intervals=parsed["intervals"],
        positions=parsed["positions"],
        pits=parsed["pits"],
        weather=parsed["weather"],
        race_control=parsed["race_control"],
    )
    context, diagnostics = build_pace_context(reconstruction.race_state, dataset, key)
    return HistoricalPaceContextResult(
        context=context,
        diagnostics=diagnostics,
        reconstruction_diagnostics=reconstruction.diagnostics,
        modelling_feed_cache_hits=cache_hits,
    )
