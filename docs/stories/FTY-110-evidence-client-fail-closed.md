---
id: FTY-110
state: merged
primary_lane: estimator
touched_lanes:
  - security-privacy
review_focus:
  - malformed-payload-fail-closed
  - validation-truncation
  - client-dedup
risk: medium
tags:
  - estimator
  - evidence
  - third-party-data
  - hardening
approved_dependencies: []
requires_context:
  - docs/contracts/food-resolution.md
  - docs/contracts/evidence-retrieval.md
  - docs/architecture/evidence-retrieval.md
  - docs/standards/testing-standards.md
  - docs/security/security-baseline.md
autonomous: true
---

# FTY-110: FDC/OFF Evidence Clients Fail Closed on Malformed Payloads (estimator)

## State

ready_with_notes

## Lane

estimator

## Dependencies

- None to schedule. This **hardens merged code**: the FDC client (FTY-044),
  the OFF barcode client (FTY-060), and the FTY-061/062/082 evidence helpers
  are all landed. This story changes only the response-validation seam inside
  `fdc.py` and `off.py`; it adds no contract and no migration.

## Outcome

A JSON-but-malformed third-party body (a non-numeric nutrient, a garbage
`serving_quantity`, a missing-but-required id, an over-long product name) no
longer **crashes the estimation worker**. The FDC and OFF clients fail closed —
mapping a non-conforming reply to their own non-retryable response-error type,
exactly as the Brave search client already does — so one bad upstream row routes
to a clean non-match / clarify instead of escaping as an unhandled
`pydantic.ValidationError`.

This closes a real hole on a documented low-trust boundary. In `fdc.py` the
`FdcSearchResponse.model_validate(raw)` calls (lines 313 and 360, in `lookup()`
and `list_matches()`) and in `off.py` the `OffProductResponse.model_validate(raw)`
call (line 313) sit **outside** the `try/except` that maps transport errors. A
`ValidationError` raised there is not one of the client's `*TransientError` /
`*ResponseError` types, so it sails past the resolvers and through
`FoodResolveStep`/`BarcodeResolveStep` in `food_step.py` (which catch only
`Fdc*Error` / `Off*Error`, lines 321-349) and takes down the run. The fix makes
fdc/off symmetric with `search.py` (line 458), which already catches
`ValidationError` and maps it to a clean `FAILED`.

## Scope

- **FDC — map `ValidationError` to `FdcResponseError`.** Bring the
  `FdcSearchResponse.model_validate(raw)` call inside the failure-mapping path so a
  non-conforming body becomes the client's existing non-retryable
  `FdcResponseError` (the type the resolver/step already fail-closed on), never an
  uncaught `ValidationError`.
- **De-duplicate `FdcClient.lookup` vs `list_matches` (fdc.py ~272-365).** The two
  methods duplicate ~30 lines (the `enabled` check, `normalize_query`, payload
  build, api-key header, transport call, and transport-error mapping). Extract a
  private `_search(query) -> FdcSearchResponse | None` that performs the request
  **and** the validation, mapping both transport errors and `ValidationError`. Both
  public methods call it, so both inherit the new handling from one home —
  `lookup` keeps taking the first energy-bearing match, `list_matches` keeps mapping
  all of them.
- **OFF — map `ValidationError` to `OffResponseError`.** Bring the
  `OffProductResponse.model_validate(raw)` call inside the failure-mapping path so a
  malformed product body becomes `OffResponseError`. (OFF has the single `lookup`
  path, so no dedup is needed — just close the gap.)
- **Truncate over-long descriptions/names instead of rejecting them.** Both
  `FdcFood.description` and `OffProduct.product_name` carry a
  `max_length=_MAX_DESCRIPTION_LEN` constraint, so today a merely-long-but-valid row
  fails validation and is lost. Replace the length **constraint** with a
  `mode="before"` field validator that **truncates** to the bound, mirroring
  `_truncate_title` in `search.py` (line 285). A long-named-but-otherwise-usable
  product should still resolve; only a structurally broken row fails closed.

## Non-Goals

- **No nutrition plausibility / kJ-vs-kcal sanity bound.** Validating that energy
  and macros are physically coherent (e.g. rejecting a kJ value mislabelled as
  kcal) is a separate estimator story. This story only stops the crash and keeps
  valid-but-long rows usable.
- **No transport changes.** The hardened fetch / SSRF policy, the LLM transport,
  and the allowlist are untouched.
- **No change to evidence-retrieval contracts or the resolver fallback ordering.**
  The resolve / clarify / non-match outcomes keep their current shapes; this only
  changes which internal exception type a malformed body produces.

## Contracts

- **None.** This is internal client behaviour. `FdcResponseError` and
  `OffResponseError` already exist and are already the fail-closed signal the
  resolvers and `food_step.py` consume; the resolve/clarify outcome shapes are
  unchanged. No contract doc needs a version bump.

## Security / Privacy

- **Hardens a documented low-trust third-party-data boundary.** OFF data is
  explicitly "uneven" community data and FDC is external; `docs/architecture/`
  `evidence-retrieval.md` treats both as untrusted until mapped. Today one
  malformed row escapes as an uncaught exception that crashes the worker and whose
  repr could echo provider input into logs. After the fix a bad row fails closed to
  a clean non-match/clarify — the same fail-closed posture `search.py` already
  holds.
- **Not a new trust boundary.** This is an existing untrusted input being hardened,
  not a new untrusted-input surface (no new image/fetch/OCR/upload path). No new
  big rock; the error mapping stays generic and never includes raw provider text.
- **Rated medium:** a third-party-data hardening on the estimation path with no
  contract change and no migration. The cost of the current bug is a crashed run on
  hostile/garbage upstream data; the fix is bounded and local.

## Acceptance Criteria

- **FDC malformed body fails closed:** an FDC reply with a non-numeric nutrient
  value (and one with a missing required `fdcId`) makes `lookup()` **and**
  `list_matches()` raise `FdcResponseError` — never a `pydantic.ValidationError`,
  never an uncaught exception. Through `food_step.py` this routes to the existing
  fail-closed non-match/clarify, not a crashed run.
- **OFF malformed body fails closed:** an OFF reply with a garbage
  `serving_quantity` (and a structurally broken `product`) makes `lookup()` raise
  `OffResponseError`, not a `ValidationError`.
- **Over-long names truncate, not reject:** an FDC `description` / OFF
  `product_name` longer than `_MAX_DESCRIPTION_LEN` no longer fails validation; the
  row resolves with the description truncated to the bound (asserted on the mapped
  `ProductFacts.description`).
- **Valid payloads resolve unchanged:** a well-formed FDC and OFF payload produces
  the same `ProductFacts` (including `content_hash`) as before — the dedup refactor
  and the truncate change are behaviour-preserving on good data.
- **Dedup refactor is internal-only:** `lookup` and `list_matches` share the
  extracted `_search`; the existing transport-error tests
  (`test_transient_transport_error_maps_to_fdc_transient`,
  `test_response_and_policy_errors_map_to_fdc_response`, and the OFF equivalents)
  still pass unchanged.
- `make verify` passes.

## Verification

- Run the backend verify hook: `cd backend && ./verify.sh` (ruff check + ruff
  format --check + mypy + pytest), i.e. root `make verify`.
- **New malformed-payload tests** in `tests/test_fdc_client.py` and
  `tests/test_off_client.py`: feed the injected transport a JSON-but-malformed body
  (non-numeric nutrient / missing `fdcId` for FDC; garbage `serving_quantity` /
  broken `product` for OFF) and assert `pytest.raises(FdcResponseError)` /
  `pytest.raises(OffResponseError)` — explicitly **not** `ValidationError` and not
  an unhandled crash. Cover both `lookup()` and `list_matches()` on the FDC side so
  the shared `_search` path is exercised twice.
- **Truncation test:** an over-`_MAX_DESCRIPTION_LEN` `description` / `product_name`
  resolves to a `ProductFacts` whose description is truncated to the bound (no
  exception raised).
- **Behaviour-preserving test:** a known-good FDC and OFF payload maps to the same
  `ProductFacts` and `content_hash` as before the change.
- The existing transport-error mapping tests remain green unchanged.

## Planning Notes

- **Audit correction — no existing crash-assertion tests to flip.** The audit note
  flagged `tests/test_fdc_client.py:147` and `tests/test_off_client.py:189` as
  `pytest.raises(ValidationError)` tests that must be inverted. Those two are
  actually `test_settings_require_https_base_url` — they assert an `http://` base URL
  is **correctly rejected at settings construction**, which stays true and must
  **not** change. There is no existing test asserting the malformed-*payload* crash,
  so the malformed-payload tests above are **new**, not edits. This is a net-add to
  the suite; nothing in the current test files needs inverting.
- **Truncate vs reject (the small decision behind `ready_with_notes`).** Recommend
  **truncate**, matching `_truncate_title` in `search.py`: a long product name is
  cosmetic, and rejecting an otherwise-usable energy-bearing row over a display
  string needlessly drops a real match. Rejection is reserved for structurally
  broken rows (bad types, missing required ids), which still fail closed.
- **`_search` is the natural single home for the fail-closed fix.** Folding the
  `ValidationError` mapping into one extracted method (rather than patching three
  call sites) is why the dedup rides along here: it guarantees `lookup` and
  `list_matches` can never drift apart on this hardening.

## Readiness Sanity Pass

- **Product decision gaps:** one small, reversible call — truncate-vs-reject for
  over-long names — recommended (truncate, to match `search.py`) and justified
  above; `ready_with_notes` only for that. No health/nutrition/behavioural question
  is involved (this is data-robustness, not guidance), so no evidence research is
  warranted.
- **Cross-lane impact:** primary estimator; security-privacy rides along
  (non-serializing) since it hardens a low-trust boundary. **Single boundary, zero
  big rocks:** no public contract change, no schema migration, no new
  untrusted-input trust boundary (an existing untrusted input is being hardened).
  Stays wholly in the estimator lane.
- **Size:** `review_focus` = 3 (malformed-payload-fail-closed, validation-
  truncation, client-dedup); `requires_context` = 5. Well under both ceilings — a
  deliberately small quick-win, kept as one story.
- **Security/privacy risk:** medium — third-party-data hardening on the estimation
  path; the fix removes a crash-on-hostile-input and an uncaught-repr log risk, with
  no new surface.
- **Verification path:** `make verify` + new FDC/OFF malformed-payload fail-closed
  tests (both `lookup` and `list_matches`) + truncation test + behaviour-preserving
  good-payload test; existing transport-error tests stay green.
- **Assumptions safe for autonomy:** yes — a local refactor of two existing clients
  with the one judgment call (truncate) pinned here, no contract, no migration, no
  external provider call (transport is injected/faked in tests), no UI.
