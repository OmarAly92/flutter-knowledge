---
name: visual-verification
description: Use after design-driven Flutter implementation/updates, or for matching-profile HTML/Figma capture, difference measurement and visual fixes. Findings-only reviews use flutter-review.
---

# Visual Verification

For implementation, read the [project configuration contract](../flutter-init/references/configuration.md) before applying package-specific instructions. Keep its conventions and naming; adapt package-specific examples through the selected mechanics.

An agent with no feedback loop declares a screen finished the moment it compiles — the largest source of "looks roughly right but is wrong" UI. This skill is the loop. It runs headless with `flutter test`: no device, no emulator, no running app.

Use the [task workflow](../flutter-knowledge/references/workflows.md) for entry and final handoff. This skill owns source comparison and its correction loop, then returns evidence to the workflow for findings-only review.

A findings-only review follows that workflow's review route: inspect existing comparison evidence and report stale or missing coverage. Do not start this capture/correction loop unless implementation or a new visual comparison run is requested. A comparison-only request authorizes its evidence capture, but UI fixes still require implementation scope.

## Required completion contract

After implementing or changing a screen from HTML or Figma, run this loop in the same task without waiting for a separate test request. For a feature, verify every affected screen separately, including design-represented states, sheets and dialogs in scope. Record the coverage before capture; one screen or one aggregate percentage cannot stand in for the feature. Shared-widget changes include the affected in-scope screens. Pure nonvisual work needs no invented screenshot coverage.

Compare the original HTML/Figma reference against the Flutter capture. A passing Flutter-to-Flutter regression test, a successful `--update-goldens`, or a clean analyzer does not establish design fidelity. Preserve the source reference; never regenerate it from Flutter.

Write `docs/design/verification.md` (or update the project's existing equivalent) with one row per screen/state/reference variant:

| Screen / state | Source and reference PNG | Capture profile | Flutter PNG / diff PNG | Overall difference | Worst region | Status / remaining differences |
| --- | --- | --- | --- | --- | --- | --- |

For the review helper, use stable plain-text screen/state/variant labels in the first column, Markdown links to one local reference PNG in the second and to the Flutter PNG then diff PNG in the fourth, and plain percentage values in the fifth and sixth. Artifact links resolve relative to this report. Supply these labels to `flutter-review` through repeated `--design-screen` arguments, including every required row from task scope.

Record the source HTML path/URL and selector/state, or Figma frame/node identity; logical size, DPR, safe-area insets, skin, locale, text scale and deterministic data; the exact comparison command, tolerance, shift, thresholds and any ignored regions with reasons. Link the artifacts and retain the command output. Report both percentages printed by the tool, rounded to two decimals. These measure pixel differences under the recorded settings, not human-perceived quality or a design accuracy score. Ignored pixels are cleared from the difference mask; the overall denominator remains the full canvas.

Use **VERIFIED** only when comparison exits 0 and inspection finds no remaining fixable mismatch. Use **DIFF** when thresholds fail or a fixable visual defect remains, even if the command passed. Use **NOT VERIFIED** when a reference, font, capture dependency, SDK or permitted command is unavailable, or capture sizes cannot be aligned; state the blocker and never invent a percentage. A stopped loop is not automatically verified. Summarize every screen's status and measured differences in the final response, with a link to the evidence.

For variants with no supplied design, record source comparison as NOT VERIFIED (no reference); regression/accessibility checks can still run separately. Whole-app planning produces proposed coverage and briefs, not captures of unimplemented Flutter screens or measured results.

## Preflight and repeatable runs

Before the first screen matrix, run the [core and capture preflight](references/preflight.md): shared-core wiring, expected-state assertions, fonts, shadows, text metrics, inputs, loading frames and the source capture profile on one or two representative rows. Apply the applicable pending-operation, disposal and combined Arabic/large-text/narrow/keyboard checks from it before spending visual rounds on polish.

For more than a couple of rows use the [verification runner](references/runner.md): one Flutter camera process, unique attempts, complete logs, artifact hashes, `compare.py --json` at default settings and a hash-bound inspection step. The runner never turns a numeric PASS into VERIFIED; the final inspection and `finalize` do. Use targeted rows while correcting and one full manifest run as the final gate.

## Reuse and concise evidence

Read the [source/reference cache contract](references/design-cache.md) before reuse. Hits only avoid redundant source extraction/capture; they never reuse Flutter output or comparison as a pass. Capture current screens and compare every required source-backed row. Extra regression variants without supplied sources remain separate coverage, not invented source-comparison requirements.

Use compare.py --json to retain structured evidence with percentages, settings, paths and bounds; exits0/1/2 and scoring remain unchanged. Keep full JSON locally and present needed status/metrics/artifact paths to the agent. Errors have no invented percentages. --allow-resize remains rough inspection only, never verified evidence.

Use an overview/contact sheet to triage all changed PNGs, then inspect ambiguous text, geometry, state, RTL or red regions at full resolution. A numeric PASS still requires inspection; unreadable details remain unchecked.

## The two pictures

Both use the same logical viewport, pixel ratio, insets, skin, locale and text scale, showing the same data and state. The default profile is 375×812 at DPR 2 — **750×1624** — but match the actual HTML viewport or Figma artboard. Adjust the capture harness size and safe area accordingly; the examples below use the default profile.

**The design (reference).** Keep it next to the design files (`design/reference/<screen>_<state>.png`), never in a `goldens/` folder.

- An HTML prototype's first screen — headless Chrome. `$CHROME` is the Chrome binary (`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` on macOS, `google-chrome` on Linux):

```bash
"$CHROME" --headless=new --disable-gpu --allow-file-access-from-files --hide-scrollbars --window-size=375,812 --force-device-scale-factor=2 --virtual-time-budget=3000 --screenshot=<reference.png> <prototype>
```

- A state reached through the prototype's JS (a tab, a sheet, a filled form) — puppeteer: `page.setViewport({ width: 375, height: 812, deviceScaleFactor: 2 })`, drive the JS with `page.evaluate`, then `page.screenshot({ path })`. Verify the saved PNG dimensions; a scaled browser preview is not a full-resolution reference.
- A Figma frame — export it at 2x.
- A prototype with a theme switch has a design per skin: capture a reference in each, and compare each skin's golden with its own.

**The screen (actual).** Use [the shared capture harness](../golden-tests/references/capture.md), composed with the configured project APIs and set up in the same state. Run its golden test with:

```bash
flutter test --update-goldens <path/to/screen_golden_test.dart>
```

During this loop `--update-goldens` is the camera, not approval. Use a candidate golden filename or preserve any approved baseline before capture; do not overwrite approved regression baselines merely to make tests pass. The capture is part of building from a design. Outside design work, new golden suites remain opt-in. A successful capture must still be compared with the source reference.

## Compare

```bash
mkdir -p build/visual_diff
python3 "<skill-directory>/scripts/compare.py" \
  --actual <goldens/screen_state.png> \
  --expected <reference.png> \
  --output build/visual_diff/<screen_state>.png
```

Resolve `<skill-directory>` from the loaded `SKILL.md` path and run the bundled script; do not copy or reimplement it. Reuse available Pillow/NumPy. If missing, install them only within the project's permitted tooling environment; otherwise report the exact prerequisite. Do not install comparison dependencies during findings-only review.

Exit codes: `0` match, `1` difference above threshold, `2` could not run (a missing file, an unreadable image, bad arguments). **A `2` is not a pass.**

Two thresholds; failing either one fails. `--threshold` (default 0.02) is the share of differing pixels in the whole image. `--max-cluster` (default 0.25) is the share in the worst cell of a 12×12 grid, so one wrong button cannot hide under the global number. `--shift` (default 2 image pixels — one logical pixel) absorbs up to one logical pixel of misalignment, such as anti-aliasing and sub-pixel text placement; a larger offset shows red, and how much of the screen it covers decides whether it fails — a small element can stay under the thresholds, so read the diff image. Each match compares the complete RGB color against a nearby pixel within channel tolerance; channel ranges from different neighbors are not combined. Calibrate expectations on the actual design and Flutter capture rather than assuming a universal renderer error rate.

A mockup's fake status bar or home indicator is not part of the screen — exclude it with `--ignore-region X,Y,W,H` in image pixels (a 44pt top bar is `0,0,750,88`). Never raise a threshold to make a screen pass.

## Read the diff

The output is the capture, faded, with differing pixels in red. The script also prints the bounding box of all differences and the densest cell — read those first, then open the image. Open it on a PASS too: a missing or extra element can stay under both thresholds.

- **Red toward the end of Latin text lines whose start lines up** — check font loading, weight, tracking and scaling first. If those match, renderer differences can remain; establish that cause from the actual captures instead of treating every text mismatch as unavoidable.
- **A whole element in red, nothing beside it** — missing from one picture or extra in it.
- **Everything shifted up or down by a status bar's height** — the two pictures disagree on the safe area. The golden harness gives 375×812 a phone's 44pt top and 34pt bottom inset; check the screen uses `SafeArea` or `AppScaffold`, and that the reference keeps the prototype's status bar area.
- **The whole block doubled and offset** — a padding, a spacing token or a text size is wrong; everything after it moves.
- **Red outlining one element's box** — its size, radius or border token.
- **A solid red block over one element** — a wrong color token, or a missing opacity.
- **Red everywhere, evenly** — check both capture profiles and image dimensions before changing the code.
- **Letters with a different shape entirely** — the font is not loaded. Check `pubspec.yaml` and the golden harness before touching the widget.

## The loop

1. Capture both pictures.
2. Compare, and read the diff image.
3. Sort what is red into what the code can fix and what it cannot or must not:
   - **The code cannot fix** a renderer difference whose cause has been verified after checking typography and capture setup.
   - **The code must not fix without revisiting the decision** a difference from an agreed scale-preserving mapping (a 28px padding built as 24, a 26px title built as 24). Follow the early design decision: exact-source authorization permits measured role tokens, never presentation literals.
4. Something the code can fix is left: fix it, never the reference. Each round carries every fix whose cause you know; a guess rides along with them, never alone. Capture the screen again and look at the golden first — a change that moved nothing needs no compare round. Then compare again.
5. Only the other kind is left: stop — whether or not the numbers pass. A PASS with red the code can fix still in the image (a box, an icon or a text placed wrong) goes on to step 4. After four rounds, only fixes whose cause you know continue — no more guesses. Report the numbers, what is still red and why, and list the off-scale values as the user's decision — add tokens through `flutter-app-theme`, or snap the design to the scale.

After four rounds, identify the remaining cause from evidence; do not assume it is a renderer limitation. Missing fonts and wrong capture profiles must be corrected or reported as verification blockers.

A size mismatch stops the script: rescaling one image to fit the other buries the real defect under edge noise. Check the agreed viewport and DPR on both captures. `--allow-resize` is for a rough look only.

## After it matches

For comparison-only work, stop with the source/Flutter/diff artifacts, measurements and inspection report. Do not promote a regression baseline, generate regression variants or start fixes unless that additional work is authorized.

For authorized design implementation, after the source comparison and PNG review pass, use `golden-tests` and its [coverage/handoff contract](../golden-tests/references/coverage-handoff.md) to preserve prior baselines, promote eligible inspected candidates and pass the ordinary regression check without `--update-goldens`. Compare each design-backed variant against its own reference; the others establish regression coverage only. Do not finish with candidates alone or treat a skipped/empty regression suite as a pass. Commit only when authorized. Later baseline updates need an intentional UI change and inspection of every changed PNG.

## What this does not catch

Each comparison covers one captured state, size and skin. Add the required coverage rows and `golden-tests` variants; static snapshots alone do not prove scrolling, animation, keyboard interaction or accessibility behavior. Passing is a floor, not a ceiling. The widget tree itself comes from `html-to-widget` or `figma-to-widget`.
