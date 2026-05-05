from app.simulation.race_engine import simulate_race


def test_simulate_race_total_laps():
    result = simulate_race(
        base_lap_time=90,
        pit_loss=22,
        strategy=[
            {"compound": "soft", "laps": 5},
            {"compound": "medium", "laps": 5},
        ],
    )

    assert result["total_laps"] == 10
    assert len(result["laps"]) == 10


def test_simulate_race_has_pit_stop():
    result = simulate_race(
        base_lap_time=90,
        pit_loss=22,
        strategy=[
            {"compound": "soft", "laps": 5},
            {"compound": "medium", "laps": 5},
        ],
    )

    pit_laps = [lap for lap in result["laps"] if lap["pit_stop"]]

    assert len(pit_laps) == 1
    assert pit_laps[0]["pit_loss"] == 22