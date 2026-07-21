# Templates — docs/design contents

## README.md (index)

- How the directory is organized (screen dirs: spec md + prompt.md + PNGs; shared docs list).
- Screen table (dir → screen).
- "Already implemented in this repo (do not re-invent)" — skin/type/motion/font/core-widget
  inventory with file paths.
- Global screen conventions (page background, app-bar paddings, decorative glow, hidden
  scrollbars, staggered entrances).
- Suggested implementation order (shell first; screens fall back to placeholders).

## colors.md

- Brand ramp table (hex).
- Semantic token table: `token | light | dark | skin getter` — flag surprises inline
  (e.g. "dark ink on green in BOTH themes").
- Derived getters worth knowing (glow, focus ring, translucent bars, scrims…).
- Shadow recipes table.

## typography.md — families table (family → wired name → usage), scale table
(getter → size/lh/tracking/weight → design usage), quirks list (display family for titles,
button weight, italic wordmark, fallback font for missing glyphs).

## motion.md — duration table, curve table (exact cubic-beziers), keyframe recipes
(name → effect → duration+curve pairing), screen-transition styles, micro-interaction list
(press scales per control).

## components.md — per shared control: exact spec line (sizes, padding, radius, colors as
token names, text style, shadow, press behavior) + the core widget that implements it.

## `<screen>/<screen>.md` — the full spec

1. Image refs at top + links to the four shared docs.
2. One-paragraph purpose/context (where it mounts, when it shows).
3. Layout tree (top → bottom) with exact paddings/sizes.
4. Per-element specs: colors as skin getters, text styles by getter name, radii/spacing
   numbers, every state (selected/disabled/done/out-of-range/today...).
5. Dummy content VERBATIM (strings, times, names) so screens match the PNGs.
6. Motion: which entrance/loop/press each element uses, with token names.
7. Behavior: interactions, gestures (verified ones marked as such), navigation.
8. Flutter mapping: feature dir, which core widgets, which parts are custom feature widgets.

## `<screen>/prompt.md` — the cleared-session brief

Written so an agent with ZERO conversation context implements the screen exactly:

1. `# TASK:` one-liner + phase scope ("UI-only — dummy data, no backend").
2. **Read these BEFORE writing any code** — the spec md, the PNGs, shared docs, and the
   actual repo files (skin, motion, core widgets, validators).
3. **Already exists — do NOT recreate** — with traps ("X exists but this design doesn't use it").
4. **Files to create** — exact tree per the template conventions in playbook §0
   (feature dir, cubit/state part files, screen/body split, one widget per file) +
   router/DI wiring notes, spelled out in the prompt itself.
5. **Key implementation points** — numbered; only the critical and easy-to-miss details
   (gesture semantics, RTL mirroring, state persistence keys, animation pairings, defaults).
6. **Dummy data** — or a pointer to the verbatim strings in the spec md.
7. **Localization** — all strings via the project's key system, languages required.
8. **Definition of done** — analyzer clean; matches the PNGs in BOTH themes; RTL correct;
   listed interactions work.

Keep each prompt ≤ ~90 lines; it references the spec md for exhaustive values instead of
duplicating them.
