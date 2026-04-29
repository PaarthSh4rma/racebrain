from app.simulation.race_engine import simulate_race


def compare_strategies(
    base_lap_time: float,
    pit_loss: float,
    strategies: list[list[dict]],
) -> dict:
    results = []

    for index, strategy in enumerate(strategies):
        simulation = simulate_race(
            base_lap_time=base_lap_time,
            pit_loss=pit_loss,
            strategy=strategy,
        )

        results.append({
            "strategy_id": index + 1,
            "strategy": strategy,
            "total_time": simulation["total_time"],
            "total_laps": simulation["total_laps"],
            "pit_stops": max(len(strategy) - 1, 0),
            "simulation": simulation,
        })

    ranked = sorted(results, key=lambda item: item["total_time"])

    return {
        "best_strategy": ranked[0],
        "ranked_strategies": ranked,
    }