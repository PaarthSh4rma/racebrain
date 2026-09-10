# V2 dependency and coupling audit

`backend/app/domain_v2` imports only the standard library, Pydantic, and sibling V2 contracts. It does not import FastAPI, frontend/React code, the OpenF1 client, OpenRouter/OpenAI, HTTP clients, environment variables, or deployment configuration. Interfaces refer only to V2 contracts and standard typing/datetime.

Current result: **no outward infrastructure dependency violations**. Pydantic is the intentionally selected contract dependency. Runtime V1 imports no V2 module, so production/API/frontend behaviour is unchanged.

The current selection port is named `CompetitorSelector`; no foundation interface claims competitor-behaviour modelling. Typed `ValidationMetric` and `ValidationResult` outputs remain, but the ValidationEngine input protocol is intentionally deferred to V2.6 when approved multi-model ValidationCase semantics exist.

`domain_v2.__init__` exposes no wildcard/package-level API; consumers import explicit submodules. Foundation contract payloads use immutable tuples and strict frozen models, with no mutable list/dict/set fields.

Future CI should retain an import-boundary test or static rule as adapters are added. Provider/API layers may import inward; reversing that dependency is a release blocker.
