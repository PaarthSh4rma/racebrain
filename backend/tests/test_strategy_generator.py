from app.simulation.strategy_generator import generate_strategies


def test_generate_strategies_returns_results():
    strategies = generate_strategies(
        total_laps=20,
        include_one_stop=True,
        include_two_stop=False,
    )

    assert len(strategies) > 0


def test_generated_strategy_laps_sum_to_total():
    total_laps = 20

    strategies = generate_strategies(
        total_laps=total_laps,
        include_one_stop=True,
        include_two_stop=False,
    )

    for strategy in strategies:
        assert sum(stint["laps"] for stint in strategy) == total_laps