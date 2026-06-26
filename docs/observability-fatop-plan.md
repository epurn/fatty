# Plan: `fatop` — Fatty agent observability TUI

A single Go binary that gives the command centre a live, pretty view of the
agent system and lets you drill into what any individual agent is doing right
now. Lives in the private command centre only — never in public `fatty/`.

## Goals

- One glanceable dashboard: are the services up, what's each agent doing, what's
  in flight, what's stuck.
- Drill into a specific agent / story / PR and read its message stream (turns,
  tool calls, verification, blockers) as it happens.
- Replace the raw `tail -F` in `agents-up.sh` with something legible.
- No new daemon: `fatop` is a read-only viewer over files + `gh`. The agents stay
  the source of truth.

## Non-goals

- Not a controller (start/stop stays in `agents-control`). A later `fatop`
  action layer is possible but out of scope here.
- Not a hosted dashboard. Local TUI + CLI only.
- Nothing about `fatop` or runner logs ever crosses into public `fatty/`.

---

## Current observability surface (what we build on)

| Source | Where | Format today |
| --- | --- | --- |
| Steward service | `fatty-steward-agent/logs/steward.{out,err}.log` | plain text lines |
| Reviewer service | `fatty-reviewer-agent/logs/reviewer.{out,err}.log` | plain text lines |
| Author (one-shot) | `fatty-worktrees/.steward-run/<ID>.log` | `claude -p` plain console text |
| Assignment | `fatty-worktrees/.steward-run/<ID>.json` | JSON |
| Running marker | `fatty-worktrees/.steward-run/<ID>.active` | timestamp; presence = live |
| Author result | `<worktree>/.fatty-author-result.json` | JSON (deleted after parse) |
| PR / check state | `gh pr list ... --json ...` | JSON |
| Process state | `pgrep`, `launchctl list \| grep com.epurn.fatty` | text |

The author is spawned by the steward via `Popen(..., stdout=log_file,
stderr=STDOUT)`, and `claude -p` currently runs **without** `--output-format
stream-json`, so the log is unstructured prose. That's the main thing blocking a
clean message-level view, so we fix it first.

---

## Milestone 1 — Structured event logging (foundation)

Give every agent one machine-readable event stream so the TUI parses one schema
instead of scraping three text formats.

### 1a. Common event envelope (JSONL)

Define and document one line-delimited JSON schema, written one event per line:

```json
{
  "ts": "2026-06-25T18:03:11.482Z",
  "agent": "steward",            // steward | reviewer | author
  "run_id": "FTY-010",           // story id, PR-<n>, or "service"
  "level": "info",               // debug | info | warn | error
  "event": "assign_story",       // stable enum per agent
  "msg": "FTY-010 ready; lane contracts available",
  "fields": { "lane": "contracts", "story_id": "FTY-010" }
}
```

Document it in `docs/agent-event-log.md` as the contract the TUI depends on.

### 1b. Author → `claude` stream-json

In `author_agent/runner.py::run_claude`, add `--output-format stream-json
--verbose` to the `claude -p` command and capture the event stream to a sidecar
file (e.g. `<ID>.events.jsonl` in `.steward-run/`) while still writing the
human log. Keep `.fatty-author-result.json` exactly as is — it remains the
authoritative RESULT the steward parses; stream-json is additive telemetry.

Wrap each Claude stream event in the common envelope (`agent: "author"`,
`run_id: <story_id>`) so tool calls, turns, and text deltas show up as discrete
events. Gate behind `FATTY_AUTHOR_STREAM_EVENTS=1` so it can be disabled.

### 1c. Steward + reviewer structured logger

Add a tiny `events.py` helper to each Python agent that emits the envelope as
JSONL to `logs/<agent>.events.jsonl`, alongside the existing human text log
(don't break `tail`-based habits). Replace the current `print(json.dumps(...))`
decision dumps and key state transitions (`assign_story`, `invoke_steward`,
`blocked PR`, `posted APPROVE`, `set reviewer-approved`, `enabled auto-merge`)
with structured `emit(event=...)` calls.

Deliverable: three agents emitting the same envelope; schema doc; feature flags.
This is the only milestone that touches agent code, so it's a discrete story per
agent (respecting the public-repo boundary — all of this is command-centre side).

---

## Milestone 2 — `fatop` read layer + CLI

Stand up the Go module and a scriptable CLI before the TUI, so the data layer is
testable on its own.

### Stack

- **Go** single binary (`fatop`), `cobra` for subcommands.
- **Bubble Tea** + **Lipgloss** + **Bubbles** (Charm) for the TUI in M3.
- `tail`-style file following via `nxadm/tail` or `hpcloud/tail`.
- `gh` shelled out for PR/check state (reuses your existing auth; no new tokens).
- *(Alt stack if preferred: Rust + `ratatui` + `crossterm`. Same architecture.)*

### Read layer (`internal/state`)

- `RunState`: scans `.steward-run/` → active runs (`.active` markers + age),
  assignments (`*.json`), per-run log + events paths.
- `Services`: `pgrep` + `launchctl` → up/down per agent.
- `PRs`: `gh pr list --json number,title,headRefName,isDraft,reviewDecision,statusCheckRollup`.
- `Events`: parse the JSONL envelope from any agent stream; tail + replay.

### CLI subcommands

```
fatop status                 # one-shot snapshot: services, active runs, PRs, stuck flags
fatop logs [agent] [-f]      # merged, color-coded event stream; --since, --level, --grep
fatop inspect <ID|PR-n>      # assignment + timeline of turns/tool-calls + verification + blockers
fatop watch                  # launch the TUI (M3)
fatop doctor                 # confirm it can read every source (paths, gh auth)
```

`status` and `inspect` reimplement the `agents-status` skill as structured,
fast, colorized output. Keep the skill as the natural-language wrapper that
shells into `fatop`.

---

## Milestone 3 — Live TUI dashboard

Bubble Tea app, `fatop watch` (also `fatop` with no args). Pretty by default,
themeable, keyboard-driven.

### Layout

```
┌ fatop ──────────────── steward ● up   reviewer ● up   authors 1/2 ─ 18:03 ─┐
│ AGENTS / RUNS              │ STREAM — author · FTY-010                       │
│ ▸ steward      ● polling   │ 18:02:55 ⚙ tool  Bash: make verify             │
│ ▸ reviewer     ● watching  │ 18:02:58 ✎ edit  apps/api/contracts.py         │
│ ▾ authors                  │ 18:03:01 ✓ turn  added estimator schema         │
│   ● FTY-010  contracts 4m  │ 18:03:09 ⚙ tool  Bash: pytest -q               │
│   ○ PR-6     blocked       │ 18:03:11 ⚠ verify make verify → FAIL           │
│ OPEN PRS                   │ ...                                             │
│   #9 approved · auto-merge │ [tail following — press / to filter, g/G jump] │
│   #6 changes-requested     │                                                 │
└ q quit · �t logs · ↵ inspect · / filter · r reload · ? help ──────────────┘
```

- **Header**: per-service status dots, active author count, clock; turns red if a
  service is down or a check failed.
- **Left rail**: agents and live runs; lane + elapsed time; color by state
  (running / blocked / idle / done).
- **Main pane**: live event stream for the selection, icon + color per event
  type (turn / tool / edit / verify / error). Tails by default; `/` to filter,
  `g`/`G` to jump, `t` to toggle raw text log vs structured events.
- **Inspect view** (`↵`): full run detail — assignment (story, lanes, required
  context), turn-by-turn timeline, verification commands + outcomes, blockers,
  resulting PR + check rollup.
- **Footer**: keybinding hints.

### Behavior

- Poll/refresh state every ~2s; tail event files continuously.
- "Stuck" heuristics surfaced visually: `.active` marker older than N minutes,
  failed checks, `changes-requested`, ready queue starved.
- Theme via Lipgloss adaptive colors (light/dark terminal aware).

---

## Milestone 4 — Wire-in & polish

- Point `agents-up.sh` at `fatop watch` instead of raw `tail -F` (keep a
  `--raw` escape hatch).
- Update the `agents-status` skill to call `fatop status`; add a short `fatop`
  section to `CLAUDE.md` and a README in the binary's repo dir.
- Build/release: `make build` → static binary in command centre; document the
  install path. Add Go to each agent's `make doctor`? No — `fatop` is operator
  tooling, doctored separately via `fatop doctor`.
- Tests: golden-file tests for the read layer against sample `.steward-run/`
  fixtures and captured stream-json.

---

## Suggested story breakdown (for the planner)

1. **OBS-1** Define event envelope + `docs/agent-event-log.md` (low risk).
2. **OBS-2** Author stream-json sidecar + flag (medium — touches author run path).
3. **OBS-3** Steward + reviewer structured logger (medium).
4. **OBS-4** `fatop` Go scaffold: read layer + `status`/`doctor` (medium).
5. **OBS-5** `fatop logs` + `inspect` (medium).
6. **OBS-6** TUI dashboard (medium).
7. **OBS-7** Wire-in: `agents-up.sh`, skill + docs update, tests (low).

Order: 1 → (2,3 parallel) → 4 → 5 → 6 → 7. Milestone 2 CLI works against
current text logs as a fallback, so `fatop` is useful even before every agent is
fully structured.

## Open decisions

- **Go vs Rust** — plan assumes Go + Bubble Tea; swap to Rust + ratatui if you
  prefer (architecture is identical).
- **Where the binary lives** — new `fatty-fatop/` dir in the command centre vs.
  under `scripts/`. Recommend its own dir with its own `CLAUDE.md`, mirroring the
  other agent repos, gitignored from the public boundary.
- **Replace vs. augment text logs** — plan augments (keeps human logs + adds
  JSONL). Cheaper rollback, slightly more disk.
