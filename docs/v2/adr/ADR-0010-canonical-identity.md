# ADR-0010 — Canonical identity semantics

**Status:** Accepted

## Context
Provider keys are convenient but unstable as domain identity and would couple every model to OpenF1. A “car” identifier can also be misread as physical chassis identity.

## Decision
RaceBrain owns opaque `EventId`, `SessionId`, `CompetitorId`, `DriverId`, and `TyreSetId` values. `CompetitorId` identifies a competitive entry in a session, never a chassis. Provider identifiers exist only in adapter DTOs, external references and provenance. Where a stable canonical natural identity exists, adapters may deterministically derive a UUID (preferably UUIDv5 using a versioned RaceBrain namespace and canonicalised natural key), but the natural key cannot be semantically defined by OpenF1.

## Consequences
Identity mapping is explicit and cross-provider records may reference one canonical entity. Natural-key canonicalisation and namespace versions require governance. Source corrections or ambiguous entrants can change a derived key; mappings must expose provenance. UUID collision risk is negligible but semantic collisions from poor canonicalisation remain possible.

## Alternatives Considered
Mandatory OpenF1 keys would create provider lock-in. Random IDs would prevent deterministic reconstruction. A new identity service is unjustified at this stage.

## Migration Impact
V2.1 defines and tests deterministic fixture/OpenF1 mapping policy without adding an external service. V1 provider IDs remain compatibility fields only.
