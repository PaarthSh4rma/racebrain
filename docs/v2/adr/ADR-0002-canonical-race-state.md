# ADR-0002 — Canonical RaceState

**Status:** Accepted

## Context
OpenF1 keys/dictionaries currently shape services and APIs, while replay and future live operation need equivalent inputs.

## Decision
All sources produce one immutable, provider-independent full-field RaceState at an aware cutoff. RaceBrain-owned opaque domain IDs are required; provider IDs are optional metadata. Competitor identity means a session entry, not a chassis. Unknown observations remain absent and provenance/data quality travel with state.

## Consequences
Models consume stable semantics; adapter mapping and stricter validation become mandatory.

## Alternatives Considered
Provider-specific model paths; a loose common dictionary. Both move coupling and ambiguity into decision code.

## Migration Impact
Historical replay becomes the first producer. A focal completed lap establishes timestamp T, while every competitor uses its own latest defensible observation at or before T. Fixture and future live adapters target the identical contract.
