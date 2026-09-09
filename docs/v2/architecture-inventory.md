# Architecture inventory

Disposition: **KEEP**, **ADAPT**, **REPLACE**, **DEPRECATE**, or **REMOVE-LATER**. Coverage describes current automated tests.

| Path/subsystem | Responsibility and I/O | Dependencies/coupling | State/determinism/tests | Risks | Disposition |
|---|---|---|---|---|---|
| `backend/app/main.py`, `config.py` | FastAPI composition and CORS; env to app | Imports all V1 routers | Stateless; startup covered | Marketing API description; single composition root is appropriate | KEEP |
| `api/simulate.py`, `strategy.py` | Dict/Pydantic inputs to deterministic toy engine | V1 simulation shapes | Stateless; engine tests | Weak bounds, no units/provenance/field model | DEPRECATE |
| `api/monte_carlo.py` | Generates/compares candidates | Track globals and V1 simulation | Seeded endpoint deterministic; hardening tests | Calls fastest-candidate frequency “win probability” | DEPRECATE |
| `api/race_engineer.py` | Bundled ranking/briefing | Same globals plus prose assembly | Un/seeded Monte Carlo; limited tests | “Engineer” authority exceeds evidence | REMOVE-LATER |
| `api/race_data.py`, `live_strategy.py` | Exposes raw provider data and full-session summary | OpenF1 leaks through API/service | Network/cache state; replay tests show leakage risk | Historical hindsight; provider schema is public contract | DEPRECATE |
| `api/replay.py` | Historical discovery and bounded assessment endpoints | Replay Pydantic/service | Cache state; strong fixture/API coverage | Good boundary, but V1 shapes and heuristics | ADAPT |
| `api/ai*.py` | Rule/LLM explanation and scenario endpoints | Untyped simulation dicts; OpenRouter | LLM nondeterministic; limited hardening | User prose can alter decision inputs; trusts client result payload | REMOVE-LATER |
| `data_sources/openf1_client.py` | HTTP, retry, bounded in-memory TTL cache | `httpx`, raw OpenF1 dictionaries | Stateful cache; extensively replay-tested | Sync blocking calls; raw schema propagates | ADAPT |
| `services/race_state_builder.py` | Whole-session weather/lap/stint summary | Global OpenF1 client | Stateful/network; indirect tests | Not canonical; averages future records and exposes keys | REPLACE |
| `services/live_strategy_service.py` | Threshold-based call | Raw dicts, hard-coded tyre ages | Deterministic; minimal coverage | Chooses final stint; no competitors/units/provenance | REPLACE |
| `models/replay.py` | Tolerant OpenF1 and replay response models | Provider names embedded | Immutable not enforced; strong replay coverage | Mixes adapter DTOs, domain state and presentation | ADAPT |
| `services/replay_service.py` | Cutoff filtering, summaries, recommendation, sampled alternatives | OpenF1 client, V1 models, globals | Seeded comparisons reproducible; extensive fixtures | Valuable no-hindsight logic mixed with fetch/model; generic wet fallback; arbitrary scores | ADAPT |
| `simulation/race_engine.py` | Simple compound pace/degradation sum | Global constants, dict stints | Deterministic; direct tests | Universal tyre constants, no fuel/traffic/conditions/calibration | REPLACE |
| `simulation/strategy_generator.py` | Exhaustive one/two-stop candidates | Three dry compounds, fixed min stints | Deterministic; direct tests | Ignores state, inventory, rules, current lap and feasibility | REPLACE |
| `simulation/strategy_engine.py` | Rank by total time | Race engine | Deterministic; indirect tests | Empty inputs unsafe; ranking is not decision support | REPLACE |
| `simulation/monte_carlo.py` | Perturb inputs and rank candidates | Global random plus race engine | Some functions unseeded; endpoint path seeded; tests indirect | Misnamed win probability; simplistic SC catch window and noise semantics | REPLACE |
| `data/track_profiles.py` | 24 circuit defaults | Unversioned hard-coded numbers | Deterministic; API coverage | No source/date/config provenance; fixed SC probability | ADAPT |
| `ai/scenario_parser.py`, `scenario_analysis.py`, `tools.py`, `router.py` | Keyword-to-adjustment and rerun | Toy simulator and arbitrary mappings | Deterministic except simulation seed omitted; little coverage | “Ferrari mode”; semantic guesses silently become model values | REMOVE-LATER |
| `ai/analysis_tools.py` | Deterministic prose | V1 win/preference keys | Stateless; little coverage | Overinterprets variance and clustered candidates | ADAPT |
| `ai/llm_client.py` | Optional OpenRouter prose | env, OpenAI client | External/nondeterministic; availability test only | “Elite engineer” framing; raw dict prompt; must remain downstream | ADAPT |
| `frontend/src/App.tsx`, styles | Single-page simulation, AI and replay shell | Direct API clients, Tailwind classes, Framer Motion | React state; Playwright responsive coverage | Marketing hero, glow/glass/card density, mixed products | REPLACE |
| `components/StrategyRanking.tsx`, `Metric.tsx`, `Slider.tsx` | Candidate cards and controls | V1 transport types | Local/presentational; browser coverage | Card ranking hides assumptions and numeric comparison | REPLACE |
| `components/ai/*`, `RaceEngineerBriefing.tsx` | AI chat/scenario/briefing UI | Client-supplied simulation object | Async/external; sparse tests | AI authority and decorative hierarchy dominate evidence | REMOVE-LATER |
| `components/replay/*` | Guided replay and bounded assessment | Replay client/types | Async; four focused browser tests | Strong workflow, but card presentation and score semantics need adaptation | ADAPT |
| `api/*.ts`, `types/*.ts` | Fetch transport and handwritten DTOs | Duplicate backend contracts | Stateless; mocked browser coverage | Drift; mixed view/transport types, loose strings | ADAPT |
| `backend/tests` | API hardening, simulation and replay fixtures | V1 modules | 38 baseline tests | Strong replay invariant; no calibration/contract separation | KEEP |
| `frontend/tests` | Replay workflow/error/overflow and responsive layout | Mock API, Playwright | Deterministic mocks | No analytical semantic assertions | KEEP |
| `.github/workflows/ci.yml` | Python 3.13 and Node 24 validation | GitHub Actions | Stateless | Local Node can differ; browser tests separate | KEEP |
| `render.yaml`, `frontend/vercel.json` | Render/Vercel deployment | Provider-specific ops config | External state | Vercel rewrite hardcodes production backend | KEEP |
| `README.md`, milestone note, screenshots | Public claims and replay invariant | V1 terminology | Static | Portfolio/AI/pit-wall positioning is stale | ADAPT |

## Technical debt that would be unacceptable in a professional strategy tool

- Unversioned universal tyre pace/degradation constants and circuit assumptions presented without provenance or calibration.
- Candidate preference frequencies duplicated under race-win terminology without a modelled competitive field.
- Provider dictionaries and IDs crossing service and API boundaries; duplicate drifting frontend shapes.
- Whole-session reconstruction paths that can expose future weather, incidents, laps and final stints.
- Free-text keyword parsing that silently changes numerical assumptions, including joke-specific behaviour.
- Randomness without an explicit seed on several decision paths and no persisted model/config identity.
- “Confidence” derived from arbitrary candidate gaps or record counts rather than calibration.
- No competitor, gap, traffic, rejoin, tyre-set inventory or measurable validation layer.
- LLM prompts framed as an elite engineer and supplied client-controlled result dictionaries.
- UI emphasis on claims and cards instead of state visibility, units, provenance, warnings and comparison tables.
- PATH-dependent local validation currently selects no `python` alias and an unsupported default Node, while CI uses Python 3.13/Node 24. V2.0 must pin and document one supported runtime for each language.
