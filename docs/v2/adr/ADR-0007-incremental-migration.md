# ADR-0007 — Incremental V1-to-V2 migration

**Status:** Accepted

## Context
V1 and replay work today; a rewrite would combine semantic, model, API and UI risk.

## Decision
Use a strangler migration inside the existing FastAPI codebase: isolated contracts, canonical replay producer, calibrated model modules, V2 APIs, then operator UI. V1 routes remain until consumers and parity tests migrate.

## Consequences
Temporary duplication and explicit compatibility mapping are accepted; microservices and new infrastructure are not.

## Alternatives Considered
Big-bang rewrite; premature services. Both increase failure and operational cost.

## Migration Impact
Follow the staged migration map. Removal is capability-gated and occurs only in a dedicated cleanup after the operator workflow, frontend migration, equivalent regression coverage, validation and zero production dependencies are demonstrated; no removal is expected before V2.5/V2.6.
