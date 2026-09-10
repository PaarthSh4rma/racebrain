# ADR-0004 — Deterministic modelling core

**Status:** Accepted

## Context
Decision paths include unseeded sampling and optional LLM prose/scenario parsing.

## Decision
Identical canonical state, model versions, configuration and seed must produce identical evaluations and recommendations. An LLM may propose a candidate structured scenario, but numerical changes must be explicit before execution. LLMs may explain completed, immutable results and may never create observed state, silently alter model state, or override decision values.

## Consequences
Seeds/configuration/model lineage are inputs and outputs; explanation failures cannot affect decisions.

## Alternatives Considered
LLM agent orchestration inside modelling; implicit global randomness. Neither is reproducible or auditable.

## Migration Impact
Keep V1 AI compatibility; introduce a downstream grounded explainer only after V2.4.
