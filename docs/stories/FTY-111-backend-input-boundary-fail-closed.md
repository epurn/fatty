---
id: FTY-111
state: merged
primary_lane: backend-core
touched_lanes:
  - security-privacy
review_focus:
  - input-validation
  - registration-race
  - fail-closed-status
  - concurrency
risk: medium
tags:
  - profile
  - auth
  - validation
  - fail-closed
  - api
approved_dependencies: []
requires_context:
  - docs/contracts/identity-and-profile.md
  - docs/security/security-baseline.md
  - docs/standards/testing-standards.md
autonomous: true
---

# FTY-111: Fail Closed at the Profile + Registration Boundary (backend)

## State

ready

## Lane

backend-core

## Dependencies

- None to schedule. This **hardens two merged write paths**: FTY-020 (auth +
  profile service) and FTY-021 (profile capture). Both are landed; this story
  changes only how each boundary handles a bad-but-plausible request, with no
  schema or contract change.

## Outcome

Two request paths that today turn a plausible-but-bad input into an unhandled
`500` are made to **fail closed with the correct 4xx**. Both are the same theme —
reject at the request boundary instead of letting a bad write reach (and crash on)
the database — so they ship in **one PR** in the serializing backend-core lane.

1. **Explicit-null on a required profile field → `422`, not `500`.**
   `PUT /api/users/{user_id}/profile` with `{"timezone": null}` (or
   `units_preference` / `metabolic_formula` null) currently passes validation,
   sets the column to `None`, and crashes on commit against a `nullable=False`
   column. It must be rejected at validation with `422`.
2. **Concurrent duplicate registration → `409`, not `500`.** Two simultaneous
   registrations of the same email both pass the existence check, and the loser
   hits the unique index on commit, raising an unhandled `500`. The loser must get
   the same `409 Conflict` the sequential duplicate path already returns.

## Scope

- **Fix 1 — required profile fields reject explicit null.** In
  `app/schemas/profile.py`, `ProfileUpdateRequest` types `metabolic_formula`,
  `units_preference`, and `timezone` as `X | None` with `default=None`, but the
  matching `UserProfile` columns (`app/models/identity.py` ~116–123) are
  `nullable=False`. The service (`app/services/profile.py` ~46–47) does
  `update.model_dump(exclude_unset=True)` then blindly `setattr`s, so a present
  explicit `null` writes `None` and the commit raises `IntegrityError` → `500`.
  **Tighten the schema** so these three fields, *when present*, may not be null:
  the field type/validator rejects an explicit null with `422` while still keeping
  them **optional in the partial-update sense** (absent = untouched, the
  documented incremental-capture behaviour). The three genuinely nullable metrics
  (`height_m`, `weight_kg`, `birth_year`) keep `X | None` and are unchanged.
- **Fix 2 — registration race returns `409`.** In `app/services/auth.py`,
  `register_user` (~66–82) does check-then-insert (`_find_local_identity` then
  `session.commit()`) with **no `IntegrityError` catch**. When two concurrent
  registers of the same email both pass the existence check, the loser violates
  `uq_auth_provider_identifier` (`app/models/identity.py` ~70–72). Wrap the commit:
  catch `IntegrityError`, `session.rollback()`, and raise
  `AuthError("conflict", "email already registered")` — the same error the
  sequential path raises, which `app/routers/auth.py` (~25) already maps to `409`.
  Mirror the existing catch-rollback-recover pattern in
  `app/services/log_events.py` (~127–139).

## Non-Goals

- **No migration and no new table.** The DB columns and indexes are already
  correct; this only stops the boundary from feeding them bad input.
- **No contract change.** Both fixes *enforce already-documented behaviour* —
  required profile fields stay required, a duplicate registration stays `409`. No
  status code or request/response shape changes, so no contract doc is bumped.
- **No auth-flow refactor** beyond adding the race catch; no change to login,
  timing-equalization, or token issuance.
- **No rate-limiting / brute-force protection** on the auth path — that is a
  separate security story.
- **Touch no other endpoint or field.** Do not re-validate the genuinely nullable
  profile metrics, and do not change the partial-update (absent = untouched)
  semantics.

## Contracts

- **None.** `docs/contracts/identity-and-profile.md` is referenced for the
  intended behaviour (required fields, `409` on duplicate register) but is **not
  modified** — these fixes make the implementation match it.

## Security / Privacy

- **Fail-closed hardening on two trust boundaries.** Both fixes convert an
  unhandled `500` (which can leak a stack trace / internal detail on a
  database-error path) into a deliberate, generic 4xx.
- **Registration timing must stay equal.** The race fix runs *after* the password
  hash + insert attempt, so it does not introduce a new fast-path that could
  re-enable email enumeration via timing. The loser still pays the full
  hash-and-attempt cost before getting `409`, matching the existing posture in
  `docs/security/security-baseline.md`. Do not move the duplicate check earlier or
  add a pre-hash existence short-circuit.
- **Object-level authorization is unchanged.** Fix 1 stays behind the existing
  fail-closed `_authorize` (cross-user profile write is still `404`).
- **Rated medium:** correctness fixes on the auth and profile write paths with a
  concurrency requirement (the unique-index race), but no migration, no contract
  change, and no new untrusted-input surface.

## Acceptance Criteria

- **Fix 1 — null rejection:** `PUT .../profile` with an explicit `null` for
  `timezone`, for `units_preference`, and for `metabolic_formula` each returns
  `422` (not `500`), and no write occurs.
- **Fix 1 — no regression:** a valid partial update still applies and returns the
  updated DTO; an omitted field is still left untouched (incremental capture); an
  out-of-bounds / invalid value still returns `422`; the nullable metrics
  (`height_m`, `weight_kg`, `birth_year`) still accept absence and valid values.
- **Fix 2 — race returns `409`:** two concurrent same-email registrations resolve
  to exactly **one** `auth_identities` row; the loser returns `409` (not `500`).
- **Fix 2 — no regression:** a sequential duplicate registration still returns
  `409`; a fresh registration still returns its normal success response and issues
  a token.
- `make verify` passes.

## Verification

- Run the backend verify hook: `cd backend && ./verify.sh` (ruff check + ruff
  format --check + mypy + pytest), i.e. root `make verify`.
- **Null-rejection tests:** parametrized `PUT .../profile` with explicit `null`
  for each of `timezone`, `units_preference`, `metabolic_formula` → `422`; assert
  the stored row is unchanged. Keep the existing valid-update and reject-invalid
  tests green.
- **Registration-race test:** drive two same-email registrations so the unique
  index fires (e.g. concurrent sessions / forced commit ordering); assert exactly
  one identity row exists and the losing call returns `409`, never `500`. Keep the
  existing sequential-duplicate `409` and happy-path registration tests green.

## Planning Notes

- **Why tighten the schema (vs drop-null-in-service) for Fix 1:** rejecting at the
  schema boundary returns the correct `422` (a validation error the client can
  act on) rather than silently dropping the field, and keeps the fix at the edge
  where the other profile validation already lives. The choice is reversible and
  low-stakes; schema-tighten is recommended. The fix must preserve the
  partial-update contract: *absent* still means "leave untouched", only *present
  and null* is rejected.
- **Why the loser raises the same `AuthError("conflict")`:** the router already
  maps `conflict → 409`, so the race path converges on the identical response as
  the sequential duplicate — one code path, one documented status.
- **The pattern already exists:** `app/services/log_events.py` (~127–139) catches
  `IntegrityError`, rolls back, and recovers; mirror its shape for the auth catch.

## Readiness Sanity Pass

- **Product decision gaps:** none. The only judgment call (schema-tighten vs
  drop-null-in-service for Fix 1) is decided and reversible. No health, nutrition,
  or behavioural question is involved, so no evidence research is warranted.
- **Cross-lane impact:** primary backend-core; security-privacy rides along
  (non-serializing). **Single boundary, zero big rocks:** no public contract
  change, no schema migration / new table, no new untrusted-input trust boundary.
  The two fixes share the "fail closed at the request boundary" theme and both
  live in the serializing backend-core lane, so they correctly bundle into one PR
  rather than splitting.
- **Size:** `review_focus` = 4 (under the 5 ceiling); `requires_context` = 3
  (under 8). Comfortably one story.
- **Security/privacy risk:** medium — auth + profile write-path correctness with a
  concurrency requirement; object-level authz unchanged; equalized registration
  timing explicitly preserved; both fixes remove a `500`-stack-leak surface.
- **Verification path:** `make verify` + null-rejection tests (per field, `422`,
  no write) + registration-race test (one row, loser `409`, not `500`) + existing
  happy-path/regression tests stay green.
- **Assumptions safe for autonomy:** yes — bounded changes to one schema and one
  service method, no migration, no contract, no UI, no external provider, with the
  pattern to mirror pinned above.
