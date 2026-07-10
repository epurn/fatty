# FTY-235 — End-of-Sweep Visual Audit, Today: findings

One in-depth, eyes-on rendering pass of the **Today** surfaces after the
accent-as-text (FTY-207..212) and type-scale (FTY-213..217) mechanical sweeps.
This is the single in-depth visual pass that replaces the per-story simulator
screenshots those sweep stories used to carry.

Captured on the iOS simulator (iPhone 17, iOS 26.5) against the E2E debug build
(`EXPO_PUBLIC_FATTY_E2E=true`, the freshly-built v1 binary + Metro), driving the
**FTY-247 visual-review presets** by deep link
(`fatty://__visual-review?preset=<name>&theme=<light|dark>`) — no manual RC
backend walking, no live state mutation. Each preset's theme is forced by the
deep-link `theme` param, so light and dark are the same synthetic fixture
switched at runtime.

## State-by-state verdict

| State | Preset | Light | Dark | Accent-as-text (accentText, AA) | Type-scale (no clip/wrap/truncate/mis-size) |
|-------|--------|-------|------|--------------------------------|---------------------------------------------|
| Populated day | `today.populated` | `today-populated-light.png` | `today-populated-dark.png` | **PASS** — hero bar fills the amber **fill** accent (`colors.accent`), correctly *not* accent-as-text; no accentText text site is reachable in this fixture (resolved entries only). Timeline source icons legible on both surfaces. | **PASS** — display hero numeral "245" renders tabular on the type scale; "245 / 2,000 kcal · 12%", "1,755 to go", P/C/F chips, "5:30 AM" cluster header, and both timeline rows render without clipping, wrapping, truncation, or mis-size. |
| Empty day | `today.empty` | `today-empty-light.png` | `today-empty-dark.png` | **PASS** — calm neutral empty state; no accent-as-text site present (empty track bar uses the neutral track, not accent). | **PASS** — "0", "0 / 2,000 kcal · 2,000 to go", 0-valued P/C/F chips, and "Log your first thing" invite all render on-scale with no clip/wrap. |
| Signed-out gate | `today.signed_out` | `today-signed-out-light.png` | `today-signed-out-dark.png` | **PASS** — the amber **Sign in** button is the accent **fill** (dark text on amber), correctly not accent-as-text; native segmented control (Sign in / Create account) renders with a clear selected state on both surfaces. | **PASS** — "Welcome back" display headline, "Signing in to localhost:8000" subtitle, segment labels, field placeholders, and button label all render on-scale, no clip/wrap. |
| Confirm-parsed sheet | `today.confirm_parsed` | `today-confirm-parsed-light.png` | `today-confirm-parsed-dark.png` | **PASS** — **"Not now"** renders `colors.accentText` — the **dark** amber `#92400E` on the white surface in light, the **bright** amber `#F5A623` on the charcoal surface in dark — i.e. the accent-as-text token, not the raw fill `accent`, and legible (AA; the `accentText`-on-surface pair is contract-tested ≥4.5:1 in `mobile/theme/theme.test.ts`). The **Looks right** button is the amber fill (dark text on amber), correctly not accent-as-text. | **PASS** — sheet hero numeral "190 kcal" renders bold on the type scale; "Granola bar" title, "Label scan" provenance, "Not yet counted" badge, "1 bar", "P 4g  C 29g  F 7g", and both action buttons render without clip/wrap/truncation. |

## Sweep-outcome summary

- **Accent-as-text (FTY-207..212):** confirmed. The one accent-as-text text site
  reachable across the four enumerated Today states — the confirm sheet's
  **"Not now"** — renders `colors.accentText` in both themes and is AA-legible
  against its surface (dark amber on white in light; bright amber on charcoal in
  dark). Every amber **fill** site (hero progress bar, Sign in / Looks right
  buttons) correctly renders the raw `accent` as a background with dark
  foreground text — the fill/text distinction the sweep established holds.
  (The additional `accentText` sites in `EntryRow.tsx` — failed-parse
  Retry/Edit-as-text actions and the "Add a detail" chip — are not exercised by
  the `today.populated` fixture, which contains only resolved entries; they are
  outside these four enumerated states and out of scope for this audit.)
- **Type-scale (FTY-213..217):** confirmed regression-free. Across all four
  states in both themes, every string renders on the `typeScale` tokens with no
  clipped, wrapped, truncated, or visibly mis-sized text; the display hero
  numerals ("245", "0", "190 kcal") render tabular and full-width with no
  jitter.

## Defects

**None observed.** All four states render on-spec in both light and dark; no
sweep-caused or pre-existing visual defect was found on Today. Accordingly there
are no `out_of_scope_bug` planner notes for this audit. (Per the story: defects
would be filed, never fixed here — this pass ships evidence only, no product
code.)
