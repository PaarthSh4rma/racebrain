# V1 to V2 migration map

Dependencies are sequential unless stated: V2.1 requires V2.0; V2.2 requires V2.1; V2.3 requires both; V2.4 requires V2.2–3; V2.5 requires V2.4 APIs; V2.6 begins with each model and becomes a product surface after V2.4; V2.7 follows exercised workflows.

## V2.0 Product Reset

- **Objective:** approve language, contracts, ADRs and boundaries.
- **Reuse/adapt:** replay invariant/tests and existing modular FastAPI composition; document all V1 code without removal.
- **New:** `domain_v2`, architecture records and contract tests.
- **Risks/tests:** premature claims, accidental runtime coupling and PATH-dependent tooling; contract immutability/unit/import tests. Pin/document one Python and one Node runtime without changing production in this pass.
- **Acceptance:** FDE approval; V1 validation unchanged; no runtime imports.
- **Non-goals:** new models, endpoints, UI, infrastructure or deployment.

## V2.1 Canonical Race State

- **Objective:** Build the first canonical historical full-field RaceState producer while preserving the no-hindsight invariant.
- **Reuse:** OpenF1 client/cache, replay tolerant parsing, cutoff logic and fixtures.
- **Adapt:** use the existing invariant and fixtures to design provider DTO/filter/mapping separation; introduce `adapters/openf1` and `application/reconstruct_state.py`. Do not copy the focal-driver implementation unchanged.
- **Legacy retained:** all V1 replay/live endpoints and V1 models.
- **Risks/tests:** timestamp ambiguity, seconds-versus-laps gaps, position absence, provider drift, hindsight leakage and per-driver N+1 provider reads; golden mapping, missing/untimed data, usable-timezone/UTC, mixed-lap full-field and adversarial future-record tests.
- **Acceptance:** focal completed lap establishes T; every included competitor, lap, weather and track-status value has defensible timing at or before T; the full field uses each competitor's own latest observation; untimed records degrade DataQuality rather than enter state; adapters use bulk reads where supported.
- **Non-goals:** pace/tyre estimates, recommendations, frontend changes.

## V2.2 Pace & Tyre Estimation

- **Objective:** versioned bounded pace/degradation and pit-loss estimates.
- **Reuse/adapt:** replay bounded laps as observations; track defaults only as labelled baselines, never truth.
- **Legacy retained:** race engine/constants and old APIs.
- **New:** `models_v2/pace`, `models_v2/tyre`, versioned configuration and validation cases.
- **Risks/tests:** fuel/traffic confounding, compound/set ambiguity, wet fallback; deterministic unit tests, residual baselines, missingness and calibration tests.
- **Acceptance:** explicit units/uncertainty/provenance; beats or honestly characterises approved naive baselines.
- **Non-goals:** field traffic, rejoin, decision calls.

## V2.3 Competitors & Traffic

- **Objective:** relative car state, relevant competitors and rejoin/traffic estimates.
- **Reuse/adapt:** canonical full-field competitors and available OpenF1 position/interval observations.
- **Legacy retained:** V1 single-car replay.
- **New:** concrete competitor/traffic behaviour model contracts and implementations, rejoin estimator, field-state adapter extensions. The foundation's `CompetitorSelector` is only a filter and is not treated as modelling.
- **Risks/tests:** sparse timing, lapped cars, pit cycles/status changes; field ordering, gap semantics, rejoin error and missing-data tests.
- **Acceptance:** lap-27 pit option reports supported nearby competitors/gaps with uncertainty and limitations.
- **Non-goals:** recommendation policy or UI redesign.

## V2.4 Strategy & Decision Engine

- **Objective:** evaluate structured actions/sensitivities and emit deterministic recommendations/triggers.
- **Reuse/adapt:** seed discipline and paired-scenario idea; discard “win probability” semantics.
- **Legacy retained:** V1 Monte Carlo, candidate generation, Race Engineer and AI routes.
- **New:** `simulation_v2`, scenario/sensitivity engine, `decision_v2`, `/v2` APIs. Recommendations select complete evaluated option IDs; raw simulation samples stay internal while DTOs expose typed estimate/quantile summaries.
- **Risks/tests:** infeasible options, correlated uncertainty, unstable rankings; determinism, property/edge, sensitivity, traceability and API contract tests.
- **Acceptance:** north-star pit/stay-out comparison includes supported time/rejoin/traffic/risk outputs and machine triggers; all lineage recorded.
- **Non-goals:** operational authority, autonomous calls, LLM decision input.

## V2.5 Operator Workbench

- **Objective:** dense operator interface consuming stable V2 contracts.
- **Reuse/adapt:** replay selection/error handling and API config; introduce transport-to-view-model mapping.
- **Legacy retained:** V1 route/shell behind explicit navigation during migration.
- **New:** state header, car table, option matrix, sensitivity/trigger/warning/provenance views.
- **Risks/tests:** information overload, semantic drift, narrow-screen comparison; browser accessibility, numeric/units, warning priority and responsive tests.
- **Acceptance:** operators can trace every displayed decision number; no decorative motion or AI-first hierarchy.
- **Non-goals:** UI before backend capability, visual claims of validation.

## V2.6 Historical Validation

- **Objective:** replay frozen predictions and compare with separately loaded outcomes.
- **Reuse/adapt:** historical discovery, fixtures, bounded states; extend case corpus.
- **Legacy retained:** historical replay UI; never remove cutoff system.
- **New:** `validation_v2`, case manifests, metric reports and validation UI.
- **Risks/tests:** leakage, survivor bias, counterfactual overclaiming; temporal isolation, reproducibility, metric and calibration tests.
- **Acceptance:** approved baseline distributions and segmented results; limitations visible; thresholds set by later FDE decision.
- **Non-goals:** claims based on OpenF1-unobservable quantities.

## V2.7 Operational Hardening

- **Objective:** harden the exercised modular monolith and retire proven-unused V1 paths.
- **Reuse/adapt:** CI, CORS, health checks and caching.
- **Legacy retained:** only consumers still within an approved deprecation window.
- **New as evidence requires:** structured observability, performance/error budgets and version compatibility policy.
- **Risks/tests:** silent model/config changes, upstream degradation; load, timeout, rollback, provider-contract and security tests.
- **Acceptance:** reproducible release manifests, monitored boundaries, documented rollback and capability-gated removals. V1 removal occurs only in a dedicated cleanup after the V2 workflow, migrated frontend, equivalent coverage, validation and zero production dependencies are proven.
- **Non-goals:** databases, brokers, auth, queues or microservices without a demonstrated requirement.
