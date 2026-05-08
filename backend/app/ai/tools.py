from app.data.track_profiles import get_track_profile
from app.simulation.strategy_generator import generate_strategies
from app.simulation.strategy_engine import compare_strategies
from app.simulation.monte_carlo import calculate_win_probabilities


def run_strategy_simulation(
    track: str,
    total_laps: int = 50,
    simulations: int = 200,
):
    profile = get_track_profile(track)

    strategies = generate_strategies(
        total_laps=total_laps,
        include_one_stop=True,
        include_two_stop=True,
    )

    deterministic = compare_strategies(
        base_lap_time=profile["base_lap_time"],
        pit_loss=profile["pit_loss"],
        strategies=strategies,
        degradation_multiplier=profile["degradation_multiplier"],
    )

    candidate_strategies = [
        item["strategy"]
        for item in deterministic["ranked_strategies"][:10]
    ]

    monte_carlo = calculate_win_probabilities(
        strategies=candidate_strategies,
        base_lap_time=profile["base_lap_time"],
        pit_loss=profile["pit_loss"],
        simulations=simulations,
        lap_variance=0.35,
        pit_variance=1.5,
        degradation_multiplier=profile["degradation_multiplier"],
        safety_car_probability=profile["safety_car_probability"],
    )

    return {
        "track": profile["name"],
        "recommendation": monte_carlo["recommendation"],
        "best_strategy": monte_carlo["best_strategy"],
        "confidence": monte_carlo["confidence"],
    }