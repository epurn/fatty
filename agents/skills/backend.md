# Backend Skill

Use for FastAPI, Postgres, Redis, Celery, auth, providers, and server-side estimation work.

## Standards

- Use typed Python and Pydantic schemas at boundaries.
- Keep route handlers thin; put behavior in services.
- Keep external systems behind adapters.
- Use migrations for schema changes.
- Validate authorization in services and tests.
- Make background jobs idempotent and safe to retry.
- Use deterministic calculators for nutrition, targets, and exercise math.
- Never let LLM output directly mutate trusted state without validation.

## Checks

When backend tooling exists, run format, lint, typecheck, unit tests, migration checks, and relevant integration tests.

