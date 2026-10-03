---
name: visual-verification
description: Closes the loop on UI built from a design — capture the screen headless as a golden (flutter test --update-goldens), capture the design at the same size (headless Chrome for an HTML prototype, a 2x export for Figma), diff them with scripts/compare.py, read the diff, fix, and repeat — four rounds of guesses, then only fixes whose cause is known. Use after building or changing a screen or widget from a design, whenever asked whether something matches the design, and before declaring UI work done. Trigger it at the end of UI work without being asked — code that compiles is not a screen that matches.
---

# Visual Verification

An agent with no feedback loop declares a screen finished the moment it compiles — the largest source of "looks roughly right but is wrong" UI. This skill is the loop. It runs headless with `flutter test`: no device, no emulator, no running app.

## The two pictures

Both are 375×812 logical pixels at pixel ratio 2 — **750×1624** — in the same skin, locale and text scale (1.0), showing the same data and state.

**The design (reference).** Keep it next to the design files (`design/reference/<screen>_<state>.png`), never in a `goldens/` folder.

- An HTML prototype's first screen — headless Chrome. `$CHROME` is the Chrome binary (`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` on macOS, `google-chrome` on Linux):

```bash
"$CHROME" --headless=new --disable-gpu --allow-file-access-from-files --hide-scrollbars --window-size=375,812 --force-device-scale-factor=2 --virtual-time-budget=3000 --screenshot=<reference.png> <prototype>
```

- A state reached through the prototype's JS (a tab, a sheet, a filled form) — puppeteer: `page.setViewport({ width: 375, height: 812, deviceScaleFactor: 2 })`, drive the JS with `page.evaluate`, then `page.screenshot({ path })`. A browser tool's own screenshot is scaled and cannot be diffed.
- A Figma frame — export it at 2x.
- A prototype with a theme switch has a design per skin: capture a reference in each, and compare each skin's golden with its own.

**The screen (actual).** The screen's golden test from `golden-tests`, set up in the same state, run with:

```bash
flutter test --update-goldens <path/to/screen_golden_test.dart>
```

During this loop `--update-goldens` is the camera — nothing is committed yet. The golden lands at 750×1624 in `goldens/` next to the test. The golden it writes is part of building from a design; outside design work, golden tests are written only when asked.

## Compare

```bash
python3 "<skill-directory>/scripts/compare.py" \
  --actual <goldens/screen_state.png> \
  --expected <reference.png> \
  --output build/visual_diff/<screen_state>.png
```

Resolve `<skill-directory>` from the loaded `SKILL.md` path and run the bundled script; do not copy or reimplement it. First run only: `python3 -m pip install --user pillow numpy`.

Exit codes: `0` match, `1` difference above threshold, `2` could not run (a missing file, an unreadable image, bad arguments). **A `2` is not a pass.**

Two thresholds; failing either one fails. `--threshold` (default 0.02) is the share of differing pixels in the whole image. `--max-cluster` (default 0.25) is the share in the worst cell of a 12×12 grid, so one wrong button cannot hide under the global number. `--shift` (default 2 image pixels — one logical pixel) absorbs up to one logical pixel of misalignment, such as anti-aliasing and sub-pixel text placement; a larger offset shows red, and how much of the screen it covers decides whether it fails — a small element can stay under the thresholds, so read the diff image. With these defaults an identical layout, Chrome against Flutter, measures 0.3–1.7% overall and up to 16% in the worst cell; what is left is Latin text drift (below).

A mockup's fake status bar or home indicator is not part of the screen — exclude it with `--ignore-region X,Y,W,H` in image pixels (a 44pt top bar is `0,0,750,88`). Never raise a threshold to make a screen pass.

## Read the diff

The output is the capture, faded, with differing pixels in red. The script also prints the bounding box of all differences and the densest cell — read those first, then open the image. Open it on a PASS too: a missing or extra element can stay under both thresholds.

- **Red toward the end of Latin text lines whose start lines up** — Flutter lays out Latin text about a quarter of a pixel per letter wider than Chrome, so a long line drifts. The renderer, not the code; Arabic does not drift.
- **A whole element in red, nothing beside it** — missing from one picture or extra in it.
- **Everything shifted up or down by a status bar's height** — the two pictures disagree on the safe area. The golden harness gives 375×812 a phone's 44pt top and 34pt bottom inset; check the screen uses `SafeArea` or `AppScaffold`, and that the reference keeps the prototype's status bar area.
- **The whole block doubled and offset** — a padding, a spacing token or a text size is wrong; everything after it moves.
- **Red outlining one element's box** — its size, radius or border token.
- **A solid red block over one element** — a wrong color token, or a missing opacity.
- **Red everywhere, evenly** — the reference is not 750×1624 at ratio 2. Fix the capture, not the code.
- **Letters with a different shape entirely** — the font is not loaded. Check `pubspec.yaml` and the golden harness before touching the widget.

## The loop

1. Capture both pictures.
2. Compare, and read the diff image.
3. Sort what is red into what the code can fix and what it cannot or must not:
   - **The code cannot fix** Latin text drift.
   - **The code must not fix** a difference that comes from a value you reported as off the token scale and mapped to the nearest token (a 28px padding built as 24, a 26px title built as 24). Matching it would mean a literal or a one-off token.
4. Something the code can fix is left: fix it, never the reference. Each round carries every fix whose cause you know; a guess rides along with them, never alone. Capture the screen again and look at the golden first — a change that moved nothing needs no compare round. Then compare again.
5. Only the other kind is left: stop — whether or not the numbers pass. A PASS with red the code can fix still in the image (a box, an icon or a text placed wrong) goes on to step 4. After four rounds, only fixes whose cause you know continue — no more guesses. Report the numbers, what is still red and why, and list the off-scale values as the user's decision — add tokens through `flutter-app-theme`, or snap the design to the scale.

Past four rounds the remaining difference is usually something the code cannot fix: a missing font, a wrong capture size, a design that changed after its screenshot.

A size mismatch stops the script: rescaling one image to fit the other buries the real defect under edge noise. It nearly always means the reference was not captured at 375×812 and ratio 2. `--allow-resize` is for a rough look only.

## After it matches

The golden that matched becomes the screen's lock: hand off to `golden-tests`, which adds the variants (the other skin, Arabic, 2× text, a small phone) and commits them. From then on `--update-goldens` is no longer a camera — it needs a reason and a look at every changed PNG.

## What this does not catch

One state, one size, one skin. Not scrolling, animation, the keyboard, larger text or right-to-left — the `golden-tests` variants cover those. Passing is a floor, not a ceiling. The widget tree itself comes from `html-to-widget` or `figma-to-widget`.
