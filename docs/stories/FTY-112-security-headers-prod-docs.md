---
id: FTY-112
state: merged
primary_lane: backend-core
touched_lanes:
  - security-privacy
review_focus:
  - security-headers
  - prod-docs-exposure
  - middleware-ordering
risk: medium
tags:
  - api
  - hardening
  - security
  - middleware
approved_dependencies: []
requires_context:
  - docs/security/security-baseline.md
  - docs/standards/testing-standards.md
autonomous: true
---

# FTY-112: Baseline Security Headers + Prod Docs Gating (backend)

## State

ready_with_notes

## Lane

backend-core

## Dependencies

- None to schedule. This **extends two merged stories**: FTY-012 (the backend
  app skeleton / `create_app` factory) and FTY-073 (the backend security pass).
  It touches only the app bootstrap in `app/main.py`; no other lane is involved.

## Outcome

The API ships baseline HTTP hardening. Today `create_app` (`app/main.py:35`)
wires **zero middleware**, so every response leaves without
`X-Content-Type-Options`, `X-Frame-Options`, or `Referrer-Policy`. And
`FastAPI(title=...)` (`app/main.py:49`) keeps `/docs`, `/redoc`, and
`/openapi.json` served **unauthenticated in every environment**, so the full API
schema is publicly browsable on a production self-host. This story adds a small
security-headers middleware and gates the interactive docs off in production —
defense-in-depth on the bootstrap, with no change to any API's shape.

## Scope

- **Add a security-headers middleware** in `create_app` that sets, on every
  response, at minimum:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY` (recommended default — the API is consumed by a
    native client, never framed; see Planning Notes for the SAMEORIGIN
    alternative)
  - `Referrer-Policy: no-referrer`
  Register it once in the factory (a `@app.middleware("http")` function or a
  small ASGI/`BaseHTTPMiddleware` class), before the routers are exercised, so it
  applies uniformly.
- **Gate the interactive docs off in production.** When
  `settings.environment == "production"` (the field is a
  `Literal["development", "test", "production"]`, `app/settings.py:39`), construct
  `FastAPI(..., docs_url=None, redoc_url=None, openapi_url=None)` so Swagger,
  ReDoc, and the raw OpenAPI schema all return `404`. In `development`/`test` the
  docs stay on (current behaviour preserved).

## Non-Goals

- **No rate-limiting** — a separate security story owns request throttling.
- **No CORS policy** — do not introduce a `CORSMiddleware` (the app has none
  today; adding one would change cross-origin behaviour). Out of scope.
- **No auth changes** — object-level authz and the bearer-token flow are
  untouched.
- **No HSTS** — `Strict-Transport-Security` and TLS termination are the
  self-hoster's reverse-proxy concern, not the app's. Note it, do not add it.
- **No Content-Security-Policy** — this is a JSON API consumed by a native
  client, so a CSP is low-value here. Optional/out-of-scope (see Planning Notes).

## Contracts

- **None.** Response security headers are additive, and the prod-only docs gating
  removes only the schema/UI endpoints in production. No request/response body or
  status shape changes for any product endpoint, so no contract doc is bumped.

## Security / Privacy

- **Defense-in-depth headers**: `nosniff` blocks MIME-confusion, `X-Frame-Options`
  blocks clickjacking framing, `Referrer-Policy` limits referrer leakage.
- **Schema exposure**: gating `/docs`, `/redoc`, and `/openapi.json` off in
  production stops the full API surface from being publicly enumerable on a
  self-host — a reconnaissance reduction, not a substitute for authz.
- **Rated medium**: it touches the app bootstrap (a broad blast radius if
  middleware ordering or the env gate is wrong) but is additive and reversible,
  with no data-model or authz change. Per `docs/security/security-baseline.md`.

## Acceptance Criteria

- Every response (e.g. the health endpoint and a sample product endpoint) carries
  `X-Content-Type-Options: nosniff`, `X-Frame-Options` (DENY), and
  `Referrer-Policy` (no-referrer).
- With `environment=production`, `GET /docs`, `/redoc`, and `/openapi.json` all
  return `404`.
- With `environment=development` (and `test`), `/docs`, `/redoc`, and
  `/openapi.json` still return `200` — current behaviour preserved.
- The headers are present regardless of environment.
- `make verify` passes.

## Verification

- Run the backend verify hook: `cd backend && ./verify.sh` (ruff check + ruff
  format --check + mypy + pytest), i.e. root `make verify`.
- Header test: assert the three headers (and their recommended values) are present
  on a sample `200` response.
- Prod docs-gating test: build the app with `environment=production` and assert
  `/docs`, `/redoc`, `/openapi.json` → `404`.
- Dev docs test: build the app with `environment=development` and assert the same
  three routes → `200`, so the gate is environment-conditional, not a blanket
  removal. (`create_app(settings=...)` already takes injected settings, so both
  cases build in-process without env mutation.)

## Planning Notes

- **Serializes on backend-core, not security-privacy.** This is a
  *security concern*, but the code change lives in `backend/app/main.py`, which the
  steward's `lane_for_path` maps to **backend-core**. The security-privacy lane
  only non-serializes for `docs/security/*` and as a tag — so `primary_lane` is
  backend-core and security-privacy rides along in `touched_lanes`. Concretely:
  this runs **back-to-back with FTY-111 on backend-core** (the lane serializes),
  not concurrently with it.
- **`ready_with_notes` for two small, reversible, pinned choices:**
  - *Header set/values:* `X-Frame-Options: DENY` is the recommended default (the
    API is never framed); switch to `SAMEORIGIN` only if a same-origin embed need
    appears. A minimal CSP is intentionally omitted (JSON API, native client);
    adding one is optional and out of scope.
  - *Env gate:* confirmed against the real enum —
    `settings.environment == "production"` over
    `Literal["development", "test", "production"]` (`app/settings.py:39`). Gate on
    exactly `production` so `development` and `test` keep the docs.
- Single boundary, no big rock: no contract change, no migration, no new
  untrusted-input trust boundary — just additive bootstrap hardening.

## Readiness Sanity Pass

- **Product decision gaps:** none load-bearing. The two judgment calls (exact
  header values; the `production` env gate) are decided and pinned above;
  `ready_with_notes` only flags them as cheaply reversible. No health/nutrition/
  behavioural question is involved, so no evidence research is warranted.
- **Cross-lane impact:** primary backend-core; security-privacy rides along as a
  tag/concern only (the code is in `app/main.py`, a backend-core path). **Single
  boundary, zero big rocks** — no public contract change, no schema migration, no
  new trust boundary.
- **Size:** `review_focus` = 3 (well under 5); `requires_context` = 2 (well under
  8). Comfortably one story.
- **Security/privacy risk:** medium — additive defense-in-depth on the app
  bootstrap; broad reach but reversible, with no authz or data-model change.
- **Verification path:** `make verify` + header-presence test + prod docs-gating
  `404` test + dev docs `200` test.
- **Assumptions safe for autonomy:** yes — a bounded, additive change to one file
  with the header values and env gate pinned here, and the env enum confirmed
  against `app/settings.py`. No external provider, no LLM, no UI.
