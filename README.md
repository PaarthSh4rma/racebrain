# RaceBrain

RaceBrain is a React and FastAPI portfolio project for reconstructing Formula 1 race state without future hindsight, modelling bounded historical evidence, and exploring generated strategy candidates under stochastic scenarios.

The model is an educational strategy simulator, not a validated physics model or a live pit-wall system. OpenF1 views query available upstream session data; their freshness depends on OpenF1 and this application does not ingest car telemetry continuously.

## Architecture

```text
React + TypeScript + Vite
        |
        | HTTP (VITE_API_URL)
        v
FastAPI
  |-- track profiles and scenario simulation engines
  |-- legacy explanation routes (not used by the public V2 UI)
  |-- cached OpenF1 boundary with controlled transient retries
  |-- cutoff-safe canonical historical reconstruction
  `-- deterministic V2 pace, tyre and robustness models
```

Circuit metadata is owned by the backend and exposed through `GET /tracks`. The frontend loads those profiles and can override base lap time and pit loss per simulation request. Monte Carlo requests may include a seed for reproducible comparisons; ordinary requests remain unseeded.

Production uses a Vercel-hosted Vite frontend calling a Render-hosted FastAPI service over HTTPS. Neither deployment includes a database or persistent application storage.

## Live deployment

- Frontend: https://racebrain-mauve.vercel.app
- Backend: https://racebrain-api.onrender.com
- API documentation: https://racebrain-api.onrender.com/docs

### Production routes

| Route | Product surface |
|---|---|
| [`/`](https://racebrain-mauve.vercel.app/) | RaceBrain product entrance |
| [`/workbench`](https://racebrain-mauve.vercel.app/workbench) | Historical Model Workbench: cutoff-safe RaceState, pace, tyre-age slope and robustness |
| [`/simulation`](https://racebrain-mauve.vercel.app/simulation) | Scenario Simulation Lab: experimental generated-candidate Monte Carlo comparison |

The historical workbench and simulation lab are intentionally separate: one analyses bounded real historical evidence, while the other explores stochastic counterfactual scenarios. Legacy AI/LLM, Race Engineer and replay UI surfaces are not part of the current public V2 product and are not called during normal use.

## RaceBrain V2 Historical Model Workbench

The production [Historical Model Workbench](https://racebrain-mauve.vercel.app/workbench) reconstructs a cutoff-safe, provider-independent `RaceState` at a selected race lap and runs the accepted V2.2 models over the same bounded full-field context. It presents representative clean-lap pace, empirical included-lap p10/p50/p90 spread, observed within-stint tyre-age pace slope and deterministic leave-one-out sign stability. Operators can inspect the exact included/excluded evidence, typed unavailable reasons, `DataQuality`, provenance, model versions and configuration hashes. These are descriptive historical estimates with explicit limitations—not normalized car performance, probabilistic confidence or strategy recommendations. The architecture and acceptance record are in [`docs/v2/v2.2.5-model-workbench.md`](docs/v2/v2.2.5-model-workbench.md).

Historical OpenF1 requests depend on upstream availability. The simulation lab does not depend on OpenF1 or OpenRouter configuration.

## Historical modelling and scenario exploration

The Historical Model Workbench reconstructs only information available at the selected completed lap, then presents canonical full-field race state, representative pace, empirical evidence spread, tyre-age pace slope, robustness, provenance and explicit limitations. The Scenario Simulation Lab keeps the useful legacy Monte Carlo engine but labels its outputs honestly: scenario preference means fastest among the generated candidates in sampled counterfactuals, not real-race win probability. See [`docs/v2/v2.2.6-product-surface.md`](docs/v2/v2.2.6-product-surface.md) for the public product boundary.

## Local setup

Backend (Python 3.11+):

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

The OpenRouter key is optional and applies only to deprecated legacy explanation endpoints; the public V2 product does not call them.

Frontend (Node 24 recommended):

```bash
cd frontend
npm ci
cp .env.example .env.local
npm run dev
```

Defaults: API `http://127.0.0.1:8000`, frontend `http://localhost:5173`.

## Environment variables

| Location | Variable | Required | Purpose |
| --- | --- | --- | --- |
| Backend | `CORS_ALLOWED_ORIGINS` | Production | Comma-separated explicit frontend origins |
| Backend | `OPENROUTER_API_KEY` | No | Enables deprecated legacy explanation endpoints only |
| Frontend | `VITE_API_URL` | Production | Public URL of the FastAPI service |

Never put a secret in a `VITE_` variable; Vite embeds those values in browser assets.

## Validation

```bash
cd backend
pytest
python -c "from app.main import app; print(app.title)"

cd ../frontend
npm ci
npm run lint
npm run build
npm run test:browser
```

GitHub Actions runs the same backend and frontend checks on pushes and pull requests.

Responsive release verification covers Chrome viewports at 390 × 844, 430 × 932, 768 × 1024, and 1440 × 900. The focused Playwright regression checks the 390px layout for document overflow, core controls, and primary-card containment.

## Deployment

### Render backend

The backend is deployed from `render.yaml` on Render's free web-service plan. Set `CORS_ALLOWED_ORIGINS` to the exact Vercel origin and optionally set `OPENROUTER_API_KEY`. The configured health check is `/health`.

Production URL: https://racebrain-api.onrender.com

For an isolated pull-request deployment, create a free Render **Service Preview**
for the backend and set Vercel's branch-specific Preview variable
`VITE_API_URL` to that preview's exact `https://…onrender.com` URL. Set the
preview backend's `CORS_ALLOWED_ORIGINS` to the exact Vercel branch-preview
origin. Do not use a wildcard, reuse an ephemeral URL in source control, or
change either production environment.

### Vercel frontend

Import the repository, set the project root to `frontend`, and set `VITE_API_URL` to the Render backend URL. `frontend/vercel.json` declares the Vite build and output directory.

Production URL: https://racebrain-mauve.vercel.app

Production environment-variable names are `CORS_ALLOWED_ORIGINS` and optional `OPENROUTER_API_KEY` on Render, plus `VITE_API_URL` on Vercel. Values should be configured in the hosting dashboards and never committed.

## Current capabilities and limitations

- Preserves 24 built-in circuit profiles and rejects unsupported identifiers.
- Compares generated one-stop and two-stop strategies with a simplified tyre-degradation model.
- Uses common sampled lap, pit, and safety-car conditions across strategies within each seeded race comparison.
- Reconstructs a driver's historical state at a selected completed lap and excludes future laps, weather, race-control messages, and pit-stop knowledge.
- Compares generated simulation candidates under paired sampled conditions; scenario preference is not real-race win probability.
- Caches repeated OpenF1 reads in bounded per-process memory with endpoint-specific expiry and retries only transient failures.
- Legacy LLM routes remain for compatibility but are absent from normal public product navigation and network traffic.
- The free Render service can spin down when idle, so the first API request after inactivity may take noticeably longer.
- There is no authentication, database, persistent telemetry pipeline, live timing operation, or production monitoring yet.

## Main endpoints

- `GET /health`
- `GET /tracks` and `GET /tracks/{track_id}`
- `POST /monte-carlo/generate`
- `GET /v2/historical/sessions`, session drivers, and available decision laps
- `POST /v2/historical/race-state` and `/v2/historical/analysis`
- Legacy AI, Race Engineer, replay, `/race-data`, and `/live-strategy` routes remain for compatibility but are not used by the public V2 UI.

## Disclaimer

RaceBrain is not affiliated with Formula 1, the FIA, or any Formula 1 team.
