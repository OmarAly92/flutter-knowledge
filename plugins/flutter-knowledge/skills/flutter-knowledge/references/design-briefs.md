# Design planning briefs

Use these structures for whole-app planning from either HTML or Figma. Read only the relevant source reader and convention skills. Record source facts separately from proposed changes; planning does not require Flutter tooling or initialize configuration. For a single-screen build, use the source directly unless a brief materially helps the task.

## README.md (index)

- How the directory is organized (screen dirs: one `<screen>.md` = spec + brief, plus PNGs;
  each screen's bottom sheets/dialogs live inside that same screen dir/md; shared docs list).
- **Screen → feature map** (dir → screen → owning feature path, e.g.
  `lib/feature/<feature>/presentation/<screen>_screen/`). This is the SINGLE source of truth for
  where each screen's UI is built; every screen brief cites its row. Derive it from the project's
  actual feature tree (via the `flutter-knowledge` and `flutter-feature-structure` skills) — a screen may launch from another
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
button weight, logo type, fallback font for missing glyphs).

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

1. Image refs at top + links to the four shared docs. Identify the HTML source/selector/state or Figma frame/node and list comparison coverage per screen/state/sheet/dialog. Record each reference profile (viewport, DPR, insets, skin, locale, text scale, data). Mark unavailable references explicitly; planning leaves Flutter results pending.
2. One-paragraph purpose/context (where it mounts, when it shows).
3. Layout tree (top → bottom) with exact paddings/sizes, the capture boundary and visible app-shell/overlay composition outside the screen subtree.
4. Per-element specs: colors as `tokens.skin` getters, text styles as `tokens.text` getters,
   radii/spacing as `tokens.radius`/`tokens.space` steps, every state (selected/disabled/done/out-of-range/today...). Record original measurements separately from implementation token mappings; when no step fits, follow `flutter-app-theme` nearest-step/add-token policy, never authorize feature literals.
5. Sample content VERBATIM (strings, times, names) so screens match the PNGs. Without an API it is written as literals in the widgets that show it, never as a fake model, data source or sample-data list ([design-only screens](../../flutter-screen-ui/SKILL.md#design-only-screens-no-api-yet)).
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

1. `# TASK:` one-liner + phase scope ("UI-only — sample content static in the widgets, no data layer, no backend").
2. **Do this FIRST, before any Dart** (state it as a hard requirement): (a) read
   `docs/design/README.md` — the screen→feature map, repo inventory, and global conventions;
   (b) invoke the `flutter-knowledge` skill, then the mini skills it maps —
   `flutter-feature-structure` (feature tree), `flutter-screen-ui` (screen/body split, UI rules),
   `flutter-state-management` (cubit), `flutter-routing-di` (routing and DI) — they are the authority. Only then read the spec sections above, the PNGs, the shared
   docs, and the actual repo files (skin, motion, core widgets, validators).
3. **Target feature — exact path (non-negotiable).** Name the owning feature and the full screen
   dir this UI belongs in (e.g. `lib/feature/<feature>/presentation/<screen>_screen/`), copied
   from the README screen→feature map. Presentation widgets and logic for this screen and its sheets/dialogs belong under this path. List integration files separately at their convention-owned locations: feature DI, core router, mirrored golden tests under `test/`, and evidence under `docs/design/`. A screen may
   be launched from a screen that lives in a different feature (e.g. opened from `home` but owned
   by its own feature); build it in ITS owning feature, never fold it into the launcher's feature.
4. **Already exists — do NOT recreate** — with traps ("X exists but this design doesn't use it").
5. **Files to create** — exact tree per the mapped feature/state/UI conventions (feature dir,
   cubit/state part files, screen/body split, one widget per file, each sheet/dialog as a feature
   widget under the same screen), plus router/DI wiring, golden harness/test paths and verification artifacts at the integration locations from (3).
6. **Key implementation points** — numbered; only the critical and easy-to-miss details
   (gesture semantics, RTL mirroring, state persistence keys, animation pairings, defaults).
7. **Sample content** — a pointer to the verbatim strings in Part A, written as literals in the widgets that show them; no fake model, data source, repository or sample-data list.
8. **Localization** — all strings via the project's key system, languages required.
9. **Definition of done** — analyzer clean; RTL correct; files placed in the correct feature from (3); listed interactions, including every sheet/dialog, work. Invoke `visual-verification` and satisfy its [per-screen completion contract](../../visual-verification/SKILL.md#required-completion-contract) for every reference-backed coverage row, including both themes when both references exist. Link the verification report with Flutter/reference/diff artifacts, measured overall and worst-region percentages and honest statuses. A missing reference or unresolved difference remains explicit; updating a golden alone is not verification.

Keep Part B tight (≤ ~90 lines); it references Part A above for exhaustive values instead of
duplicating them.
