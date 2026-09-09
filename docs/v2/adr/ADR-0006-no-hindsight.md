# ADR-0006 — Historical no-hindsight invariant

**Status:** Accepted

## Context
Milestone 2 correctly prevents later laps, weather, control events and stint endpoints entering a historical decision, while the legacy live summary leaks them.

## Decision
A historical application-level DecisionContext uses a full-field RaceState containing only observations demonstrably knowable by the cutoff. CarState, WeatherState and TrackStatusState carry observed-at times; included laps require completion times. Canonical validation normalises usable aware timestamps to UTC and proves nested observations do not postdate their enclosing car or cutoff. A focal completed lap may establish T; other competitors use their own latest defensible observation at or before T, not the focal lap number. Untimed records are excluded and reflected in DataQuality. Outcome loading occurs only after prediction is frozen.

## Consequences
Incomplete cases produce warnings rather than inferred future context; cutoff provenance and excluded counts are auditable.

## Alternatives Considered
Filter only by lap number; reconstruct from complete-session aggregates. Both permit leakage.

## Migration Impact
Preserve and extend the invariant rather than copying the focal-driver implementation. Reuse fixtures, add mixed-lap full-field and adversarial leakage tests, and build the first canonical producer.
