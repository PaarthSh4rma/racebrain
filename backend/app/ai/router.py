from app.ai.tools import run_strategy_simulation


def route_user_query(message: str):
    lowered = message.lower()

    if "pit" in lowered or "strategy" in lowered:
        result = run_strategy_simulation(
            track="monaco",
            total_laps=50,
            simulations=200,
        )

        return {
            "response": (
                f"Recommended strategy: "
                f"{result['recommendation']}"
            ),
            "tools_used": [
                "strategy_simulator"
            ],
            "tool_output": result,
        }

    return {
        "response": (
            "I could not determine which strategy tool to use."
        ),
        "tools_used": [],
    }