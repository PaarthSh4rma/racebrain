# RaceBrain V2 target architecture

RaceBrain remains a modular FastAPI application. The north-star lap-27 undercut question maps to state reconstruction, pace/tyre estimates, competitor/rejoin modelling, option simulation, sensitivity evaluation and structured triggers. Historical validation uses the same path with a cutoff-bound adapter.

```text
OpenF1 replay adapter ─┐
future live adapter ──┼─> canonical observations/RaceState
fixture adapter ──────┘              │
                                     v
                      pace | tyre | competitor models
                                     │
                                     v
                     strategy simulator -> scenario/sensitivity engine
                                     │
                                     v
                              decision engine
                               /           \
                    API/workbench       replay validation
                           |
                  optional grounded explainer
```

## Boundaries and dependency rule

`FastAPI routes -> application services -> domain_v2 contracts/interfaces`. Adapters and model implementations depend inward. `domain_v2` imports only Python/Pydantic. OpenF1 DTO parsing and unit conversion live in `app/adapters/openf1`; raw dictionaries never cross that boundary. API response mapping and future frontend-generated types live outside the domain.

Forbidden dependencies are `domain_v2 -> OpenF1/FastAPI/httpx/OpenRouter/frontend/deployment` and `decision engine -> LLM`. An explainer may consume a completed recommendation and cited inputs, but cannot mutate values or feed the decision pipeline.

## Practical modules

- `domain_v2`: opaque RaceBrain IDs; immutable full-field state/value contracts; estimate semantics; registered trigger metrics; model ports.
- `adapters/openf1`: tolerant provider DTOs, UTC/unit normalisation, provenance and no-hindsight filtering.
- `application`: orchestration, model/config selection, deterministic seed creation and result assembly.
- `models_v2/{pace,tyre,competitor}`: calibrated implementations behind small ports. Configuration is versioned data beside each model, not global constants.
- `simulation_v2`: option evaluation with deterministic configuration and seed.
- `decision_v2`: comparison policy and trigger production from evaluations.
- `validation_v2`: frozen validation cases, observed outcomes and metric calculation. It must never make future outcomes visible to reconstruction.
- `api/v2`: request/response translation only, introduced after contracts and producers are validated.
- frontend: API client DTOs and view models separate transport shape from display formatting.

All observations are validated first as provider DTOs, normalised, then validated as canonical contracts. Adapters should prefer session-level/bulk provider reads and avoid per-driver N+1 requests where the provider supports bulk access; request efficiency remains an adapter concern. Every decision-relevant estimate carries unit, model name/version/config hash, assumptions and uncertainty/provenance where applicable. Future typed, version-controlled configuration belongs under `backend/config/models/{pace,tyre,pit_loss}`. Configuration content hash and seed are recorded with results so identical state/version/config/seed is reproducible.

RaceState is always the canonical full field. A focal competitor's completed decision lap may establish cutoff timestamp T, but every other competitor is reconstructed from its own latest defensible observation at or before T; the focal lap number is never imposed across the field. The historical adapter owns cutoff enforcement before canonical construction, and validation outcomes are loaded only after prediction is frozen. DecisionContext is an application-level immutable value referencing RaceState, a focal competitor and horizon; RaceState alone owns as-of semantics. A future audit record may persist state, versions, evaluations, recommendation and execution time outside `domain_v2`; no database abstraction is introduced now.

An LLM may propose a candidate structured scenario from human language, but every numerical change must be explicit and operator-visible before deterministic execution (for example degradation multiplier `1.00 -> 1.15`). An LLM is never a source of observed RaceState and cannot silently alter model state.

## Identity and trigger policy

Canonical IDs are opaque RaceBrain values. When a stable natural identity exists, a V2 adapter may derive a deterministic UUIDv5 from a versioned RaceBrain namespace and canonicalised provider-independent natural key. Mapping provenance must record the derivation. Namespace/canonicalisation changes are versioned because semantic collisions and source corrections are a greater practical risk than UUID collisions; no identity service is introduced.

Trigger operands use the closed `TriggerMetric` registry: `GAP_AHEAD_S`, `GAP_BEHIND_S`, `INTERVAL_TO_COMPETITOR_S`, `DEGRADATION_S_PER_LAP`, `PACE_DELTA_S_PER_LAP`, `PIT_LOSS_S`, `REJOIN_MARGIN_S`, `TYRE_AGE_LAPS`, `RAIN_CROSSOVER_LAPS`, and `TRACK_STATUS`. A metric reference may identify a subject and, only where meaningful, a relative competitor. Operators are `GT`, `GTE`, `LT`, `LTE`, `EQ`, `NE`, and `CHANGES_TO`. There are no arbitrary strings, executable expressions or LLM-generated code.

## Runtime standardisation debt

V2.0 must select and document one supported Python runtime and one supported Node runtime, aligned between local setup and CI, so validation does not depend on PATH accidents. The foundations pass does not change production runtimes or dependencies.
