# Templates — docs/design contents

## README.md (index)

- How the directory is organized (screen dirs: one `<screen>.md` = spec + brief, plus PNGs;
  each screen's bottom sheets/dialogs live inside that same screen dir/md; shared docs list).
- **Screen → feature map** (dir → screen → owning feature path, e.g.
  `lib/feature/<feature>/presentation/<screen>_screen/`). This is the SINGLE source of truth for
  where each screen's UI is built; every screen brief cites its row. Derive it from the project's
  actual feature tree (via the `flutter-knowledge` skill) — a screen may launch from another
  feature's screen yet belong to its own feature; the map records the OWNER, not the launcher.
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

## `<screen>/<screen>.md` — spec + implementation brief (ONE file per screen)

One file per screen holds BOTH the full visual spec and a cleared-session implementation brief, so
the agent that builds the screen builds everything in it — body, states, and every bottom sheet /
dialog the screen opens — in a single pass. Never split the brief into a separate `prompt.md`, and
never give a sheet/dialog its own dir.

### Part A — Spec

1. Image refs at top + links to the four shared docs.
2. One-paragraph purpose/context (where it mounts, when it shows).
3. Layout tree (top → bottom) with exact paddings/sizes.
4. Per-element specs: colors as skin getters, text styles by getter name, radii/spacing
   numbers, every state (selected/disabled/done/out-of-range/today...).
5. Dummy content VERBATIM (strings, times, names) so screens match the PNGs.
6. Motion: which entrance/loop/press each element uses, with token names.
7. Behavior: interactions, gestures (verified ones marked as such), navigation.
8. Flutter mapping: feature dir, which core widgets, which parts are custom feature widgets.

### Sheets & dialogs owned by this screen

For each bottom sheet or dialog this screen opens, a subsection HERE (not a separate dir/file):
trigger, image refs (PNGs in this same screen dir), layout tree + per-element specs at the same
depth as Part A, states, motion, dismissal/behavior, and the core widget it builds on. Only
promote a sheet/dialog to a shared core widget documented in `components.md` if it is genuinely
opened from many screens.

### Part B — Implementation brief (cleared-session)

Written so an agent with ZERO conversation context implements the screen AND all its
sheets/dialogs exactly:

1. `# TASK:` one-liner + phase scope ("UI-only — dummy data, no backend").
2. **Do this FIRST, before any Dart** (state it as a hard requirement): (a) read
   `docs/design/README.md` — the screen→feature map, repo inventory, and global conventions;
   (b) invoke the `flutter-knowledge` skill — it is the authority on the feature tree, screen/body
   split, cubit, routing and DI. Only then read the spec sections above, the PNGs, the shared
   docs, and the actual repo files (skin, motion, core widgets, validators).
3. **Target feature — exact path (non-negotiable).** Name the owning feature and the full screen
   dir this UI belongs in (e.g. `lib/feature/<feature>/presentation/<screen>_screen/`), copied
   from the README screen→feature map. EVERY file for this screen and its sheets/dialogs goes
   under this path and nowhere else — never create or edit files in another feature. A screen may
   be launched from a screen that lives in a different feature (e.g. opened from `home` but owned
   by its own feature); build it in ITS owning feature, never fold it into the launcher's feature.
4. **Already exists — do NOT recreate** — with traps ("X exists but this design doesn't use it").
5. **Files to create** — exact tree per the template conventions in playbook §0 (feature dir,
   cubit/state part files, screen/body split, one widget per file, each sheet/dialog as a feature
   widget under the same screen) + router/DI wiring notes — all under the target feature from (3).
6. **Key implementation points** — numbered; only the critical and easy-to-miss details
   (gesture semantics, RTL mirroring, state persistence keys, animation pairings, defaults).
7. **Dummy data** — or a pointer to the verbatim strings in Part A.
8. **Localization** — all strings via the project's key system, languages required.
9. **Definition of done** — analyzer clean; matches the PNGs in BOTH themes; RTL correct; files
   placed in the correct feature from (3); listed interactions, including every sheet/dialog, work.

Keep Part B tight (≤ ~90 lines); it references Part A above for exhaustive values instead of
duplicating them.
