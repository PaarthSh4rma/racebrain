from app.ai.tools import run_strategy_simulation


def route_user_query(
    message: str,
    track: str = "monaco",
    total_laps: int = 50,
    simulations: int = 200,
):
    lowered = message.lower()

    if "pit" in lowered or "strategy" in lowered or "run" in lowered:
        result = run_strategy_simulation(
            track=track,
            total_laps=total_laps,
            simulations=simulations,
        )

        return {
            "response": f"Recommended strategy: {result['recommendation']}",
            "tools_used": ["strategy_simulator"],
            "tool_output": result,
        }

    return {
        "response": "I could not determine which strategy tool to use.",
        "tools_used": [],
    }