import random
from statistics import mean, stdev

from app.simulation.race_engine import simulate_race

def apply_randomness(
    base_lap_time: float,
    lap_variance: float,
) -> float:
    return random.gauss(base_lap_time, lap_variance)


def run_monte_carlo_strategy(
    strategy: list[dict],
    base_lap_time: float,
    pit_loss: float,
    simulations: int = 500,
    lap_variance: float = 0.35,
    pit_variance: float = 1.5,
) -> dict:
    total_times = []

    for _ in range(simulations):
        simulated_base_lap = apply_randomness(base_lap_time, lap_variance)
        simulated_pit_loss = max(15.0, random.gauss(pit_loss, pit_variance))

        result = simulate_race(
            base_lap_time=simulated_base_lap,
            pit_loss=simulated_pit_loss,
            strategy=strategy,
        )

        total_times.append(result["total_time"])

    return {
        "strategy": strategy,
        "simulations": simulations,
        "average_total_time": round(mean(total_times), 3),
        "best_case": round(min(total_times), 3),
        "worst_case": round(max(total_times), 3),
        "std_dev": round(stdev(total_times), 3) if simulations > 1 else 0,
    }


def compare_monte_carlo_strategies(
    strategies: list[list[dict]],
    base_lap_time: float,
    pit_loss: float,
    simulations: int = 500,
    lap_variance: float = 0.35,
    pit_variance: float = 1.5,
) -> dict:
    results = []

    for index, strategy in enumerate(strategies):
        result = run_monte_carlo_strategy(
            strategy=strategy,
            base_lap_time=base_lap_time,
            pit_loss=pit_loss,
            simulations=simulations,
            lap_variance=lap_variance,
            pit_variance=pit_variance,
        )

        results.append({
            "strategy_id": index + 1,
            **result,
        })

    ranked = sorted(results, key=lambda item: item["average_total_time"])

    return {
        "best_strategy": ranked[0],
        "ranked_strategies": ranked,
    }