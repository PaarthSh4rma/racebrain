# RaceBrain V2 domain glossary

This glossary is normative for V2. “AI” is not a domain concept.

| Term | RaceBrain meaning |
|---|---|
| Event | A named motorsport meeting at a circuit; independent of any provider event key. |
| Session | One timed competitive session within an Event, identified by a RaceBrain ID. |
| RaceState | Immutable, provider-independent full-field facts and bounded observations knowable at one cutoff. Competitors may be on different laps at that instant. It is not a forecast. |
| DecisionPoint | Application-level immutable context combining an existing RaceState, focal CompetitorId and decision horizon. It is not a persisted aggregate and does not duplicate cutoff semantics. |
| CarState | Observed state of one competitive session entry, keyed by CompetitorId: position/gaps when known, driver, tyre, recent laps, and pit state. It never identifies a physical chassis. |
| CompetitorState | A CarState interpreted relative to the focal car, optionally enriched only by competitor-model estimates. |
| Gap | Strict non-negative separation expressed as exactly one of seconds or positive whole laps. Endpoints and direction must be named. |
| Interval | Difference between adjacent classified cars, normally seconds; not interchangeable with gap to leader. |
| Position | One-based classified running order at the cutoff; absent when not reliably observed. |
| TrackStatus | Controlled race-control state carried inside a timestamped TrackStatusState; absent when no defensible observation exists. |
| WeatherState | Latest cutoff-bounded environmental observation with explicit units, observed-at time and provenance. |
| TyreCompound | Controlled compound family: Soft, Medium, Hard, Intermediate, Wet, or Unknown. |
| TyreSet | A physically distinct set where identity is known; availability is observed metadata, not inferred allocation. |
| TyreSetState | Compound, age and optional set/stint identity at a particular RaceState. |
| TyreAge | Completed usage in laps including prior use when known; never negative. |
| Stint | Consecutive race laps on one tyre set, bounded by start and optional known end. |
| PitLoss | Estimated elapsed-time cost in seconds relative to staying on track under stated track status. |
| PitWindow | Inclusive lap interval in which a planned stop remains strategically admissible. |
| Rejoin | Predicted post-stop position, gaps and nearby cars; always a model estimate. |
| TrafficState | Relevant cars, gaps, pace relationships and overtaking constraints around a projected path/rejoin. |
| PaceEstimate | ModelEstimate of representative lap time in seconds per lap under stated conditions. |
| DegradationEstimate | ModelEstimate of tyre-related lap-time change in seconds per lap per additional tyre lap. |
| ModelEstimate | Numeric value with unit, model version, assumptions, uncertainty and provenance. |
| Uncertainty | Explicit distribution family, interval, standard deviation or samples; absence means not quantified, not zero. |
| StrategyAction | Machine-readable instruction: stay out, pit now, pit in a lap/window with tyre choice, or reconsider. |
| StrategyPlan | Ordered non-empty sequence of StrategyActions. |
| StrategyOption | Identified plan offered for evaluation. |
| StrategyEvaluation | Modelled consequences and risks for one complete option under one state/configuration/seed. Distribution summaries use typed estimate uncertainty, never raw sample vectors. |
| DecisionTrigger | Machine-evaluable registered metric reference/operator/threshold that activates a StrategyAction; it contains no expression or code. |
| DecisionRecommendation | Preferred evaluated option ID, complete evaluations, confidence, assumptions, warnings, change triggers and model lineage. |
| Observation | A measured or provider-reported fact with a defensible UTC observation/completion time and provenance. Untimed historical records are excluded and reported through DataQuality. |
| Provenance | Source, version, timestamps, provider metadata, transformations and assumptions supporting a value. |
| DataQuality | Completeness/fitness assessment and explicit missing-field warnings; not model confidence. |
| ModelVersion | Stable model name, version and configuration content hash required to reproduce an estimate. |
| ValidationCase | Frozen input cutoff, configuration, prediction and separately acquired observed outcome. |
| Counterfactual | Modelled outcome for an action not taken; never labelled observed truth. |
| No-Hindsight Cutoff | Latest instant whose information may enter a historical decision; later observations and outcome-derived metadata are excluded. |

Probability is reserved for a defined event and sample space. Confidence is an assessment of recommendation support. Preference share is the frequency an option ranks first among the compared candidate set; it is not race-win probability.

Canonical `EventId`, `SessionId`, `CompetitorId`, `DriverId`, and `TyreSetId` are opaque RaceBrain-owned identities. `CompetitorId` identifies the entry represented in a session. Provider keys are external references only.
