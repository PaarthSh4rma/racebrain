from app.data.track_profiles import get_track_profile
from app.simulation.strategy_generator import generate_strategies
from app.simulation.strategy_engine import compare_strategies
from app.simulation.monte_carlo import calculate_win_probabilities


def run_strategy_simulation(
    track: str,
    total_laps: int = 50,
    simulations: int = 200,
    adjustments: dict | None = None,
):
    profile = get_track_profile(track)
    adjustments = adjustments or {}

    profile = {
        **profile,
        **{
            key: value
            for key, value in adjustments.items()
            if key in profile
        },
    }

    base_lap_time = profile["base_lap_time"]
    pit_loss = profile["pit_loss"]
    degradation_multiplier = profile["degradation_multiplier"]
    safety_car_probability = profile["safety_car_probability"]

    if "base_lap_time_multiplier" in adjustments:
        base_lap_time *= adjustments["base_lap_time_multiplier"]

    if "pit_loss_multiplier" in adjustments:
        pit_loss *= adjustments["pit_loss_multiplier"]

    pit_variance = 1.5
    if "pit_variance_multiplier" in adjustments:
        pit_variance *= adjustments["pit_variance_multiplier"]

    include_one_stop = True
    include_two_stop = True

    if adjustments.get("max_stops") == 1:
        include_two_stop = False

    strategies = generate_strategies(
        total_laps=total_laps,
        include_one_stop=include_one_stop,
        include_two_stop=include_two_stop,
    )

    deterministic = compare_strategies(
        base_lap_time=base_lap_time,
        pit_loss=pit_loss,
        degradation_multiplier=degradation_multiplier,
        strategies=strategies,
    )

    candidate_strategies = [
        item["strategy"]
        for item in deterministic["ranked_strategies"][:10]
    ]

    monte_carlo = calculate_win_probabilities(
        strategies=candidate_strategies,
        simulations=simulations,
        lap_variance=0.35,
        base_lap_time=base_lap_time,
        pit_loss=pit_loss,
        degradation_multiplier=degradation_multiplier,
        safety_car_probability=safety_car_probability,
        pit_variance=pit_variance,    
        )

    return {
        "track": profile["name"],
        "recommendation": monte_carlo["recommendation"],
        "best_strategy": monte_carlo["best_strategy"],
        "confidence": monte_carlo["confidence"],
    }