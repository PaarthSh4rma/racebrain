# V2 dependency and coupling audit

`backend/app/domain_v2` imports only the standard library, Pydantic, and sibling V2 contracts. It does not import FastAPI, frontend/React code, the OpenF1 client, OpenRouter/OpenAI, HTTP clients, environment variables, or deployment configuration. Interfaces refer only to V2 contracts and standard typing/datetime.

Current result: **no outward infrastructure dependency violations**. Pydantic is the intentionally selected contract dependency. Runtime V1 imports no V2 module, so production/API/frontend behaviour is unchanged.

Future CI should retain an import-boundary test or static rule as adapters are added. Provider/API layers may import inward; reversing that dependency is a release blocker.
