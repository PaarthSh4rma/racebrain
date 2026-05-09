import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=env_path)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY"),
)


def generate_race_engineer_response(
    question: str,
    simulation_result: dict,
    analysis: dict,
):
    prompt = f"""
You are an elite Formula 1 race engineer.

You MUST ONLY use the provided simulation data and analysis.

Do NOT invent statistics, lap times, or strategy outcomes.

QUESTION:
{question}

SIMULATION RESULT:
{simulation_result}

ANALYSIS:
{analysis}

Your task:
- Explain the strategy naturally
- Sound like a real race engineer
- Keep responses under 250 words
- Use short paragraphs
- Use bullet points where appropriate
- Explain uncertainty clearly
- Mention risks when relevant
"""

    try:
        completion = client.chat.completions.create(
            model="openrouter/free",
            messages=[
                {
                    "role": "system",
                    "content": (
                        """
                            You are an elite Formula 1 race engineer speaking to strategists on the pit wall.

                            Your responses should:
                            - sound technical but natural
                            - explain uncertainty clearly
                            - reference racecraft and strategy tradeoffs
                            - avoid generic AI phrasing
                            - avoid excessive verbosity
                            - be concise and analytical
                            - format answers cleanly with markdown
                        """
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            temperature=0.4,
        )

        return completion.choices[0].message.content

    except Exception as e:
        return f"LLM generation failed: {str(e)}"