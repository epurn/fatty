---
id: FTY-121
state: merged
primary_lane: governance
touched_lanes: []
risk: low
tags:
  - governance
  - dependabot
  - expo
  - mobile
  - supply-chain
approved_dependencies: []
requires_context:
  - .github/dependabot.yml
  - mobile/package.json
review_focus:
  - ignore-rule-coverage
  - schema-validity
  - sdk-governed-scope
autonomous: true
---

# FTY-121: Dependabot — Ignore Expo-SDK-Governed Mobile Deps (governance)

## State

ready

## Lane

governance

## Dependencies

- None to schedule. Config-only addition under `.github/` (governance per the
  steward's `lane_for_path`) — no app code changes, no blocking story.

## Related

<!-- Cross-references only — NOT scheduling dependencies. Kept out of the
     Dependencies section above so the steward's metadata_dependencies parser
     does not read these IDs as blockers (which would deadlock 121 <-> 122). -->

- Extends the merged governance work in **FTY-108** (which added the `/mobile`
  npm ecosystem to `.github/dependabot.yml`).
- **FTY-122** (Expo SDK upgrade) is the *only* mechanism by which the packages
  ignored here legitimately advance. The two can land in either order: this
  story stops the doomed individual PRs, FTY-122 moves the whole pinned set
  coherently.

## Outcome

Dependabot stops opening mobile npm PRs that cannot pass CI. The mobile app is an
**Expo SDK 56 managed project**: `expo`, `react`, `react-native`, `jest-expo`,
the `jest` version, and the eslint toolchain are all **pinned by the SDK** and
must move together via an SDK upgrade. Today Dependabot proposes bumps to these
packages individually, and each one fails mobile CI — on 2026-06-28 four such PRs
(react patch, the react-native minor group, jest 30, eslint 10) were all closed
after failing on peer `ERESOLVE` / `jest-expo` preset breakage / `eslint-plugin-react`
incompatibility. Adding `ignore` rules for the SDK-governed packages means
Dependabot only proposes mobile bumps that can actually pass CI (genuinely
independent libraries), while the SDK-governed set advances exclusively through
the Expo SDK upgrade (FTY-122). This removes recurring dead PRs and review noise.

## Scope

- **Add an `ignore:` block to the existing `/mobile` `npm` ecosystem entry** in
  `.github/dependabot.yml` (the `github-actions`, `uv`, `docker`, and the rest of
  the `npm` entry are unchanged). Ignore the Expo-SDK-governed packages so
  Dependabot stops proposing them:
  - **Pin-locked exactly by the SDK — ignore all updates:** `expo`, `react`,
    `react-dom`, `react-native`, `react-test-renderer`, `jest`, `jest-expo`,
    `@types/jest`.
  - **eslint toolchain — ignore major (and breaking) bumps**, which is what broke
    CI: `eslint`, `eslint-plugin-*` (wildcard), `@typescript-eslint/*` (wildcard).
    Scope these to major-version updates (`update-types: ["version-update:semver-major"]`)
    so in-SDK-range patch/minor lint bumps can still flow; the eslint 10 / plugin
    incompatibility was a major bump. See Planning Notes on the wildcard +
    update-type syntax.
- **Keep the file valid, schema-correct Dependabot v2 config** — the `ignore`
  entries use the documented `dependency-name` (glob-capable) + optional
  `update-types` fields.
- **Leave a short comment** in the `/mobile` block stating *why* these are
  ignored (SDK-governed; move via `expo install` / the SDK upgrade, FTY-122) so a
  future reader does not "helpfully" delete the rules.

## Non-Goals

- **No dependency bumps and no SDK upgrade here** — that is FTY-122. This only
  changes which update PRs Dependabot opens.
- **No change to the other ecosystems** (`github-actions`, `uv`, `docker`) or to
  the grouping/limit/schedule of the `npm` entry — only an `ignore:` block is
  added.
- **No auto-merge / merge automation** — unrelated to this story.
- **No app code, CI workflow, `package.json`, or lockfile edits** — config
  coverage only. The `mobile/package.json` is read-only here, used to confirm the
  ignored package names match the actual pinned deps.

## Contracts

- No public product contract. The only changed artifact is
  `.github/dependabot.yml` (a repo governance config). `mobile/package.json` is
  referenced read-only to confirm package names.

## Security / Privacy

- **Net supply-chain-neutral-to-positive, config-only.** It does not stop
  security updates for genuinely independent mobile libraries (those keep
  flowing); it suppresses update PRs for SDK-governed packages that cannot be
  applied in isolation anyway — those advance through the supported SDK upgrade
  path (FTY-122), which is the correct way to take their security fixes too.
- No secrets, tokens, machine paths, or private automation cross into the public
  repo — Dependabot `ignore` rules reference only public package names. No new
  trust boundary, no runtime behaviour change; nothing executes until a proposed
  bump is independently reviewed and merged.

## Acceptance Criteria

- `.github/dependabot.yml` is valid YAML and a schema-valid Dependabot v2 config.
- The `/mobile` `npm` entry gains an `ignore:` block; its `schedule`,
  `open-pull-requests-limit`, and `groups` are unchanged; all other ecosystem
  entries are untouched.
- The ignore block covers, at minimum: `expo`, `react`, `react-dom`,
  `react-native`, `react-test-renderer`, `jest`, `jest-expo`, `@types/jest` (all
  update types), and `eslint`, `eslint-plugin-*`, `@typescript-eslint/*`
  restricted to major-version updates.
- Each ignored package name is real — it appears in `mobile/package.json` (or is a
  wildcard that matches packages there).
- A comment in the `/mobile` block explains the SDK-governed rationale and points
  at the SDK-upgrade path (FTY-122).
- No dependency versions, app code, workflows, or lockfiles are modified. Root
  `make verify` stays green (config-only).

## Verification

- **YAML + schema:** confirm the file parses as YAML and conforms to the
  Dependabot v2 schema (local YAML parse + schema lint; e.g.
  `python -c "import yaml; yaml.safe_load(open('.github/dependabot.yml'))"`).
  **Note:** authoritative Dependabot config validity is confirmed by GitHub once
  pushed (the Dependabot config validation in the repo's Insights/Security tab);
  local checks cover YAML well-formedness and schema shape only.
- **Name reality check:** assert each non-wildcard ignored package name appears in
  `mobile/package.json`, and that the wildcards (`eslint-plugin-*`,
  `@typescript-eslint/*`) match at least one dep there.
- **Regression:** root `make verify` passes (config-only; no app surface touched).

## Planning Notes

- **Ignore syntax.** Dependabot `ignore` entries take `dependency-name` (supports
  `*` glob, so `eslint-plugin-*` and `@typescript-eslint/*` are valid) and an
  optional `update-types` list. Omitting `update-types` ignores **all** updates
  (correct for the pin-locked set); restricting to
  `["version-update:semver-major"]` ignores only major bumps (correct for the
  eslint toolchain, so SDK-compatible patch/minor lint updates still flow). If
  GitHub's current resolver rejects a particular glob, fall back to listing the
  concrete plugin names present in `mobile/package.json` and note the gap.
- **Why not ignore the whole npm ecosystem.** The point is to keep Dependabot
  useful for genuinely independent mobile libraries while silencing only the
  SDK-governed ones — a targeted `ignore` block, not removing the ecosystem.
- No evidence research warranted — this is a build/supply-chain hygiene decision
  the SDK's pinning already dictates, not a health/nutrition/behavioural question.

## Readiness Sanity Pass

- **Product decision gaps:** none. The one judgment call — glob vs. explicit
  plugin names if a glob is rejected — has a clean documented fallback. `ready`.
- **Sizing decision:** one boundary — **governance** only, zero big rocks (no
  public contract change, no schema migration, no untrusted-input trust
  boundary): a single `ignore:` block in one config file. `review_focus` = 3 (well
  under 5); `requires_context` = 2 (well under 8). Comfortably one story.
- **Cross-lane impact:** none — config-only under `.github/`; `mobile/package.json`
  read-only. No app code in any serializing lane.
- **Security/privacy risk:** low — does not suppress security updates for
  independent libs; no secrets cross into the public repo; no runtime change.
- **Verification path:** YAML parse + schema check + package-name reality check +
  root `make verify`; GitHub confirms config resolution post-push.
- **Assumptions safe for autonomy:** yes — a bounded, reversible config addition
  with its one judgment call (glob fallback) pinned here. No app code, no UI.
