from itertools import product
from typing import Literal

Compound = Literal["soft", "medium", "hard"]

COMPOUNDS: list[Compound] = ["soft", "medium", "hard"]


def generate_one_stop_strategies(total_laps: int) -> list[list[dict]]:
    strategies = []

    for first_stint_laps in range(8, total_laps - 7):
        second_stint_laps = total_laps - first_stint_laps

        for first_compound, second_compound in product(COMPOUNDS, repeat=2):
            if first_compound == second_compound:
                continue

            strategies.append([
                {"compound": first_compound, "laps": first_stint_laps},
                {"compound": second_compound, "laps": second_stint_laps},
            ])

    return strategies


def generate_two_stop_strategies(total_laps: int) -> list[list[dict]]:
    strategies = []

    for first_stint_laps in range(6, total_laps - 11):
        for second_stint_laps in range(6, total_laps - first_stint_laps - 5):
            third_stint_laps = total_laps - first_stint_laps - second_stint_laps

            if third_stint_laps < 6:
                continue

            for compounds in product(COMPOUNDS, repeat=3):
                if len(set(compounds)) < 2:
                    continue

                strategies.append([
                    {"compound": compounds[0], "laps": first_stint_laps},
                    {"compound": compounds[1], "laps": second_stint_laps},
                    {"compound": compounds[2], "laps": third_stint_laps},
                ])

    return strategies


def generate_strategies(
    total_laps: int,
    include_one_stop: bool = True,
    include_two_stop: bool = True,
) -> list[list[dict]]:
    strategies = []

    if include_one_stop:
        strategies.extend(generate_one_stop_strategies(total_laps))

    if include_two_stop:
        strategies.extend(generate_two_stop_strategies(total_laps))

    return strategies