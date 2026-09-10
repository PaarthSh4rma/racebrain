# ADR-0003 — Provider adapter boundary

**Status:** Accepted

## Context
OpenF1 is useful public data but cannot define RaceBrain or future customer integrations.

## Decision
OpenF1 HTTP, tolerant DTOs, field mapping, timestamp/unit normalisation and source-specific missingness remain in an outer adapter. Raw provider dictionaries cannot cross into V2 application/model code.

Adapters prefer provider-supported session/bulk reads over obvious per-driver N+1 access. This efficiency policy does not enter domain contracts.

## Consequences
Mapping tests and provenance are required; providers can be replaced independently.

## Alternatives Considered
Use OpenF1 models everywhere; build a generic provider abstraction with no race use case. Rejected for lock-in and speculation respectively.

## Migration Impact
Reuse the client initially, split replay parsing/filtering into the adapter, then stop exposing raw V2 responses.
