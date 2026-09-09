# Legacy boundaries

Nothing is removed during foundations work.

| Legacy boundary | Why it remains | Replacement and removal gate | Compatibility |
|---|---|---|---|
| `simulation/race_engine.py` | Powers V1 simulation APIs/UI | Versioned pace/tyre models plus V2 simulator; remove after V1 endpoint retirement | Preserve V1 responses until consumers migrate |
| `simulation/monte_carlo.py` | Powers ranking, engineer and AI flows | V2 scenario/sensitivity simulation with honest distributions | Keep misleading keys only on V1 routes |
| `simulation/strategy_generator.py` | Supplies current demo candidates | State/inventory-aware structured option generator in V2.4 | No shared V2 action dictionaries |
| `data/track_profiles.py` | All current circuit defaults and `/tracks` | Provenanced, versioned model configuration | Adapt values only after baselines; do not silently reinterpret |
| `/monte-carlo/*` | Current frontend contract | `/v2` workbench endpoints after semantic acceptance | Capability-gated deprecation; remove only in a dedicated cleanup after V2.5/V2.6 gates pass |
| AI analysis/scenario stack | Current optional experience | Grounded explainer downstream of immutable recommendation; structured scenario inputs | Disable decision-input mutation before removal |
| Race Engineer UI | Existing V1 consumer | Operator recommendation/evidence view after V2.4 | Maintain while V1 is accessible; relabel during UI migration |
| `App.tsx` marketing shell | Hosts all existing flows | Operator workbench composition in V2.5 | Route/feature coexistence during strangler period |
| `StrategyRanking` | Displays V1 preference results | Tabular StrategyEvaluation comparison | Preserve V1 field interpretation, never map it to race-win probability |

Historical replay is not disposable. Its discovery, tolerant parsing, cutoff derivation, exclusion rules, counts, warnings, cache handling and deterministic fixtures inform V2.1, but the focal-driver implementation is not copied unchanged. V2.1 builds the first canonical historical full-field RaceState producer while preserving the invariant: no observation unavailable by timestamp T may influence state. A focal completed lap establishes T; each competitor uses its own latest defensible observation at or before T. The heuristic recommendation and scorer remain V1.

V1 deprecation is capability-gated, not date-gated. Removal requires an operating V2 workflow, migrated production frontend, equivalent regression coverage, model validation, and confirmation that no production dependency remains. No V1 removal is expected before V2.5/V2.6, and removal must be a dedicated cleanup change.
