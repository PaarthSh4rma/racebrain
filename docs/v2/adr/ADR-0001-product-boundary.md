# ADR-0001 — RaceBrain V2 product boundary

**Status:** Accepted

## Context
V1 is presented as an AI simulator/pit-wall experience despite simplified, unvalidated models and public data.

## Decision
RaceBrain V2 is a race-strategy decision-support workbench for reconstruction, estimation, option evaluation, triggers, replay and validation. It is not a validated team pit-wall replacement. Calculated capability and limitations must be explicit.

## Consequences
Professional semantics and validation precede claims or visual redesign; unsupported outputs stay absent.

## Alternatives Considered
Continue the portfolio simulator; claim operational equivalence. Both obscure evidence limitations.

## Migration Impact
Keep V1 running while V2 contracts/endpoints mature; audit public language before later release.
