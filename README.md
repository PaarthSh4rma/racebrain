# RaceBrain 🏎️🧠

AI-powered Formula 1 strategy intelligence platform combining Monte Carlo simulation, semantic scenario analysis, and grounded AI race engineering.

---

## Overview

RaceBrain is an AI-assisted motorsport strategy platform designed to simulate and analyse Formula 1 race strategy decisions under uncertain race conditions.

The system combines:

* probabilistic Monte Carlo race simulation
* tyre degradation modelling
* safety car variability
* semantic AI scenario parsing
* deterministic race analysis tools
* grounded LLM-powered engineering explanations

Rather than functioning as a simple chatbot wrapper, RaceBrain behaves like an AI race engineer capable of:

* evaluating strategies
* rerunning simulations under modified conditions
* comparing outcomes
* generating contingency guidance
* reasoning about race scenarios

---

## Features

### Monte Carlo Strategy Simulation

* Generates and evaluates race strategies
* Simulates:

  * tyre degradation
  * pit stop losses
  * race variance
  * safety car probability
* Calculates:

  * win probability
  * confidence levels
  * average race time
  * strategy rankings

---

### AI Race Engineer

RaceBrain includes a hybrid AI reasoning layer capable of:

* deterministic strategy analysis
* grounded LLM explanations
* semantic scenario interpretation
* contingency generation

Example prompts:

```txt
Why is this strategy best?
```

```txt
What if degradation increases by 20%?
```

```txt
What if it rains?
```

```txt
What if Ferrari is the pit crew?
```

---

### Semantic Scenario Engine

RaceBrain can convert natural language race scenarios into structured simulation adjustments.

Examples:

| User Scenario                      | Simulation Mutation                                   |
| ---------------------------------- | ----------------------------------------------------- |
| "What if it rains?"                | Increased degradation + higher safety car probability |
| "What if degradation rises?"       | Tyre wear multiplier increase                         |
| "What if safety cars increase?"    | Increased safety car likelihood                       |
| "What if Ferrari is the pit crew?" | Increased pit stop variance (We are checking😭)        |

The system then:

1. mutates race assumptions
2. reruns Monte Carlo simulation
3. compares outcomes
4. generates contingency guidance

---

## Architecture

```text
Frontend (React + Tailwind)
        ↓
FastAPI Backend
        ↓
AI Orchestration Layer
 ├── Deterministic Analysis Tools
 ├── Semantic Scenario Parser
 ├── Monte Carlo Simulation Engine
 └── Grounded LLM Reasoning
        ↓
Strategy Recommendations
```

---

## Tech Stack

### Frontend

* React
* TypeScript
* Tailwind CSS
* Vite

### Backend

* FastAPI
* Python
* Pydantic

### AI / Simulation

* Monte Carlo simulation
* Semantic scenario parsing
* OpenRouter LLM integration
* Deterministic analysis tooling

---

## AI Engineering Concepts Demonstrated

RaceBrain was built to explore real-world AI systems engineering concepts including:

* probabilistic simulation
* deterministic AI tooling
* grounded LLM reasoning
* semantic parsing
* orchestration pipelines
* tool routing
* scenario mutation
* agentic multi-step workflows
* simulation comparison systems

---

## Running Locally

### Backend

```bash
cd backend

pip install -r requirements.txt

uvicorn app.main:app --reload
```

Backend runs on:

```txt
http://127.0.0.1:8000
```

---

### Frontend

```bash
cd frontend

npm install

npm run dev
```

Frontend runs on:

```txt
http://localhost:5173
```

---

## API Endpoints

### Strategy Simulation

```http
POST /race-engineer/briefing
```

### Deterministic AI Analysis

```http
POST /ai/explain
```

### Grounded LLM Analysis

```http
POST /ai/llm-explain
```

### Scenario Mutation + Rerun

```http
POST /ai/scenario
```

---

## Example Scenario Flow

```txt
User:
"What if degradation rises and safety cars increase?"
```

RaceBrain:

1. Parses semantic race conditions
2. Applies simulation mutations
3. Reruns Monte Carlo strategy engine
4. Compares original vs modified results
5. Generates contingency guidance

---

## Future Improvements

### V3 Roadmap

* FastF1 / OpenF1 telemetry ingestion
* Historical race replay
* Live strategy adaptation
* Telemetry visualisation
* Multi-agent strategist debate
* RAG over historical race data
* Driver-specific tyre models

---

## Disclaimer

RaceBrain is an educational and portfolio project inspired by Formula 1 strategy systems and motorsport analytics workflows.

It is not affiliated with Formula 1, FIA, or any F1 team.

---

## License

MIT License.
