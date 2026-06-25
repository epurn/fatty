---
name: plan-stories
description: The single planning entry point for Fatty. Interview the user one question at a time to resolve a rough idea into one or more ready stories, exploring the codebase instead of asking whenever possible, then write the story files. Use whenever the user wants to plan, shape, scope, or "get grilled on" a feature/change/idea, or turn an idea into stories for the steward to assign. Planning only — never implements, reviews, assigns, or operates the agents.
---

# Plan Stories

This is the planner's workbench. You interview the user until the design is
resolved, then turn the result into one or more ready Fatty stories. One grilling
session may produce a single story or a set of dependent stories when the work is
too big for one vertical slice — hence "stories".

Hard boundaries: planning only. Never implement, review, assign, launch authors,
or operate the steward/reviewer services — the steward picks up ready stories on
its own. Keep `fatty` free of any private automation detail; stories describe
product work only.

_Interview style adapted from Matt Pocock's `grill-me`._

## 1. Ground yourself first

Before asking anything, read so your questions and recommendations are informed:

- `fatty/docs/stories/README.md` — story format, the template, and the readiness
  rule (including the Readiness Sanity Pass).
- `fatty/docs/stories/v1-roadmap.md` — roadmap, ordering, and the lane vocabulary.
- The architecture / contract / standards / security docs the idea touches.
- **Explore the `fatty/` codebase.** Anything the code, docs, or roadmap can
  answer, you answer yourself and confirm — do not interrogate the user for it.

Note the next free story id by scanning existing `FTY-###` stories and the
roadmap.

## 2. Grill, one question at a time

Walk down each branch of the design tree, resolving dependencies between
decisions one-by-one until you reach shared understanding. Rules:

- **One question at a time.** Wait for the answer before the next.
- **Recommend an answer to every question** — your best call with a one-line
  why. Use the AskUserQuestion tool when the choice is discrete (put your
  recommendation first); ask in prose when it's open-ended.
- **Explore before asking.** Resolve from the codebase/docs whenever you can.
- **Relentless but convergent** — stop when the open branches are resolved.
- **Watch the scope.** If it won't fit one vertical slice, plan to split it into
  several dependent stories and grill each slice's boundary.

Resolve everything a ready story needs — these map directly to the template:

- **outcome** — the user- or system-visible result.
- **scope** — the single vertical slice; **non-goals** — what's explicitly out.
- **primary_lane** + **touched_lanes** — from the roadmap's lane vocabulary.
- **dependencies / approved_dependencies** — which stories must merge first; any
  new dependency the author is allowed to add.
- **contracts** — API, DB, job, estimator, provider, or mobile/backend DTO
  boundaries touched (these need explicit contracts).
- **security / privacy** — data touched, retention, and what untrusted input is
  involved (LLM output, fetched pages, OCR, prompts, tool output).
- **acceptance criteria** + **verification** commands.
- **risk** — low/medium/high. Estimate big when unsure. This drives the model the
  author/reviewer use: low→haiku, medium→sonnet, high→opus. Anything touching
  auth, privacy, contracts, estimator, migrations, CI gates, or branch
  protection is high.
- **autonomous** — is this safe to hand to an autonomous author as-is, or does it
  need a human product decision first? If it needs a decision, that's a blocker
  to resolve now or a reason to mark the story `ready_with_notes`/`candidate`.
- **review_focus**, **tags**, **requires_context** as relevant.

## 3. Reflect the shared understanding

When the tree is resolved, summarize the decisions (and, if splitting, the story
breakdown and dependency order) back in a few lines and get a final confirmation.

## 4. Write the story / stories

Delegate the writing to the **planner** subagent (Agent tool,
`subagent_type: "planner"`) so the role boundary holds, passing the resolved
decisions. The planner writes each story under `fatty/docs/stories/` using the
template and YAML front matter from the stories README, with:

- the assigned `FTY-###` id(s) and correct dependency links between split stories,
- a completed **Readiness Sanity Pass** (product-decision gaps, cross-lane
  impact, security/privacy risk, verification path, assumptions safe for
  autonomy),
- `state: ready` when it passes cleanly, `ready_with_notes` if it's ready but
  carries caveats, or `candidate` if an open product decision remains.

Stop at promoted, ready stories. Do not assign, launch, or operate anything.
