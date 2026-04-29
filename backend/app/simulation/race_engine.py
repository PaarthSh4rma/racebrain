from typing import Literal

Compound = Literal["soft", "medium", "hard"]


TYRE_BASE_PACE = {
    "soft": -0.8,
    "medium": 0.0,
    "hard": 0.6,
}

TYRE_DEGRADATION = {
    "soft": 0.16,
    "medium": 0.10,
    "hard": 0.07,
}


def calculate_lap_time(
    base_lap_time: float,
    compound: Compound,
    tyre_age: int,
) -> float:
    compound_delta = TYRE_BASE_PACE[compound]
    degradation = TYRE_DEGRADATION[compound] * tyre_age

    return round(base_lap_time + compound_delta + degradation, 3)


def simulate_stint(
    base_lap_time: float,
    compound: Compound,
    stint_laps: int,
) -> list[dict]:
    laps = []

    for tyre_age in range(stint_laps):
        lap_time = calculate_lap_time(
            base_lap_time=base_lap_time,
            compound=compound,
            tyre_age=tyre_age,
        )

        laps.append({
            "lap_in_stint": tyre_age + 1,
            "compound": compound,
            "tyre_age": tyre_age,
            "lap_time": lap_time,
        })

    return laps


def simulate_race(
    base_lap_time: float = 90.0,
    strategy: list[dict] | None = None,
    pit_loss: float = 22.0,
) -> dict:
    if strategy is None:
        strategy = [
            {"compound": "medium", "laps": 20},
            {"compound": "hard", "laps": 20},
        ]

    all_laps = []
    total_time = 0.0
    race_lap = 1

    for stint_index, stint in enumerate(strategy):
        stint_laps = simulate_stint(
            base_lap_time=base_lap_time,
            compound=stint["compound"],
            stint_laps=stint["laps"],
        )

        for lap in stint_laps:
            lap["race_lap"] = race_lap
            lap["stint"] = stint_index + 1

            total_time += lap["lap_time"]

            if lap["lap_in_stint"] == 1 and stint_index > 0:
                total_time += pit_loss
                lap["pit_stop"] = True
                lap["pit_loss"] = pit_loss
            else:
                lap["pit_stop"] = False
                lap["pit_loss"] = 0.0

            lap["cumulative_time"] = round(total_time, 3)
            all_laps.append(lap)

            race_lap += 1

    return {
        "strategy": strategy,
        "pit_loss": pit_loss,
        "total_laps": len(all_laps),
        "total_time": round(total_time, 3),
        "laps": all_laps,
    }