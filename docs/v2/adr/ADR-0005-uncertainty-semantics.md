# ADR-0005 — Uncertainty and estimate semantics

**Status:** Accepted

## Context
V1 uses standard deviation, “confidence,” preference and “win” terminology without consistent mathematical meaning.

## Decision
Every estimate names its value, unit, model name/version/config hash and assumptions. A point estimate does not require invented spread. Uncertainty names its representation (empirical, normal, quantile, bounded or unspecified); intervals include construction/coverage where applicable and empirical P10/P50/P90 are supported. Missing uncertainty is not zero. Probability, confidence, data quality and descriptive scenario frequency remain separate concepts.

## Consequences
Some future fields remain absent until supported; UI/API must not collapse distinct concepts.

## Alternatives Considered
One universal normal distribution; generic confidence percentage. Both fabricate precision.

## Migration Impact
V1 names remain compatibility-only; all V2 fields follow `units-and-semantics.md`.
