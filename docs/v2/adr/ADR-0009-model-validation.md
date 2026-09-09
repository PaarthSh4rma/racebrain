# ADR-0009 — Model validation as a product capability

**Status:** Accepted

## Context
Plausible-looking outputs and generic constants provide no evidence of predictive utility.

## Decision
Historical validation is a first-class module and operator capability. Frozen predictions are compared with later observed quantities using declared metrics, segments and uncertainty-calibration diagnostics. Acceptance thresholds derive from baseline distributions and FDE approval.

## Consequences
Models ship with versions, validation cases, limitations and regression evidence; OpenF1-only blind spots remain explicit.

## Alternatives Considered
Visual plausibility review; arbitrary accuracy targets. Neither supports defensible acceptance.

## Migration Impact
Define cases/metrics alongside each model, establish baselines before replacement, and expose results in V2.6.
