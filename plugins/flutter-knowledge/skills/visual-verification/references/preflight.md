# Core and capture preflight

Run this before building the first design-backed screen and again when core or the capture harness changes. It finds shared-foundation and capture defects while they are cheap, instead of discovering them as red pixels in every row. It proves wiring, not design fidelity.

For an existing-screen refresh with unchanged core/harness, reuse applicable preflight evidence only when its inputs still match; run affected checks when dependencies change or prior proof is missing. Continue the screen's behavior and capture checks below. Findings outside the authorized UI/core scope are reported, not permission to repair unrelated services. A proven blocker in the actual screen/capture dependency returns to the implementation workflow's [core readiness gate](../../flutter-knowledge/references/workflows.md#core-readiness-during-implementation); comparison-only and findings-only review report it without fixes. A blocker remains unresolved until the required work is actually verified.

## Shared core

Prove the core actually works, not just that files exist. Exercise the project's own contracts through a focused test or the capture harness, using the configured mechanics:

- Resolve every core registration through the real app registration entry (consumer/client, network status, skin registry, preferences, logger, root state owners). An unregistered or differently scoped dependency fails here, not in the first feature.
- Build `AppTheme.of(skin)` for every built-in and JSON skin; read each token group through `context.tokens`; select a skin through its owner and see the root rebuild. A theme extension absent from `ThemeData` fails here.
- Load English and Arabic, resolve a key and a missing key, switch locale and confirm direction.
- Render the principal text, scaffold/app bar, container, spaces, buttons (enabled, disabled, loading), fields (focus, error), sheet and feedback wrappers under light/dark, both locales and a larger text scale.
- Drive the API consumer against a fake transport: success, wrapped and unwrapped envelope, validation error, timeout/cancel/connection failure mapping, and that the Failure boundary — not a transport type — leaves the data layer.
- Confirm a backend URL is an explicit configuration value; do not call a live server.

## Capture calibration

Before the full matrix, capture one or two representative source rows and read them at full resolution:

- The harness mounts the expected root and state. Assert it with finders (screen type, key text) so a wrong route, loading skeleton or error state fails the capture instead of producing a plausible image.
- Dimensions, DPR, safe area, skin, locale, text scale, pointer and focus come from the row's profile; nothing is inherited from a default.
- Fonts come from the project's bundled files for both scripts, never the test fallback. Compare glyph shapes and the wrapping of a long line against the source.
- Shadows are enabled and animations are advanced to the settled frame the source was captured at; a mid-transition drawer or sheet is not a settled state.
- Inputs show the intended text, caret and placeholder; loading rows show the intended frame.
- Source capture used the same profile and the extraction covered the whole capture boundary (see `captureComposition`). Content outside the screen subtree is implemented or consciously excluded.

Fix in-scope harness and shared-widget defects found here once, before they multiply across rows. Inspect other consumers before shared changes; unresolved impact beyond the task needs a scope decision.

## Behavior checks before polish

Run the checks the feature actually has, before spending visual rounds:

- Pending operations: overlapping taps/submissions, a response arriving after a newer request, and the owner closed while a request is pending. No state is emitted after close; controllers and subscriptions are disposed.
- Drive the actual routed screens and controls: typing must update enabled/send actions, submission must show its pending state, and completion must show the new message or destination screen. Assert each visible transition; seeded owner state in a capture alone does not prove that descendants rebuild or route effects work.
- Combined layout: Arabic with larger text scale at a narrow width, with the keyboard open on a screen with fields. Automatic keyboard avoidance must work without capture/test scrolling helpers (including forced `ensureVisible`); production focus/inset management must be exercised as actual UI behavior and reported explicitly. Assert the actual field and caret stay inside the scroll viewport and above any fixed footer, rather than only above the keyboard. Verify inset consumption does not apply the keyboard twice. A deliberately scrolled capture is labeled and tested separately.
- Interaction targets keep their tap size and semantics under scale and RTL.

## Correction rhythm

Iterate with targeted rows, not the whole matrix: capture only affected rows with `run_verification.py`, compare, fix every known cause. After the changes settle run the complete manifest once as the final gate, then the repository's final review. Retain every attempt; do not edit a manifest or reference to make a row pass.

## Reusable component calibration

Before a source-backed foundation handoff or the first screen matrix, calibrate a small set of **actual core consumers** in every supplied skin. Use the applied `AppTheme`, existing wrappers and [shared capture](../../golden-tests/references/capture.md) for bundled fonts, enabled shadows and settled frames. Reuse that harness; do not build a separately styled replica, render engine or CSS converter. This is component/camera evidence, never full-screen fidelity.

Keep the source **layout viewport** separate from the **output crop**. Mount Flutter at the source viewport with the app's actual ScreenUtil design size and scale policy, then crop both full camera PNGs at identical integer image-pixel edges. A component crop is not a new ScreenUtil design size. Preserve full captures and source facts from `layoutTree` / `captureComposition` / the [foundation snapshot](../../set-theme-from-html/references/helpers.md#browser-snapshot). Inspect the original source state and retain its scripts, styles, resources and renderer identity.

Use `scripts/calibrate.py` additively; existing runner/comparator commands and settings remain unchanged:

```bash
python3 "<visual-verification-directory>/scripts/calibrate.py" run --manifest calibration.json --out <new-attempt-dir>
python3 "<visual-verification-directory>/scripts/calibrate.py" finalize --manifest calibration.json --results <attempt>/results.json --inspection inspection.json --out <new-reviewed-dir>
python3 "<visual-verification-directory>/scripts/calibrate.py" check --manifest calibration.json --results <reviewed>/results.json
python3 "<visual-verification-directory>/tests/test_calibration.py"
```

`run` retains full comparator logs, crops, diff PNGs, measurements, profiles and SHA-256 identities. It uses `compare.py --json` with unchanged defaults, no resizing, ignored pixels or threshold overrides. Exit 0 means all supported measurements and PNG comparisons passed numerically; 1 means DIFF; 2 means missing/unsupported evidence. Numeric PASS remains **NOT VERIFIED** until inspection. Output directories must be new and outside input inventories.

### Export actual runtime observations

The optional `scripts/calibration_probe.dart` is a widget-test observation adapter, not an app harness. Copy/import it into a task-local test using existing Flutter/test dependencies and the workflow's installed Python 3 for SHA-256 binding; it adds no package dependency. Assert the expected wrappers, visible text, state and loaded fonts before capture. Observe inside the existing harness's capture callback, while shadows and the row's environment are active:

- `calibrationTypography(RenderParagraph)` reads the effective render span after Material/default-style merging, including `letter_spacing`, size, weight and explicit line height. Select the actual label's `RichText` descendant, not a token getter or `Text.style`. Null line height and rich spans are unsupported here; export separate measured runs/line metrics through a reviewed adaptation rather than guessing. Compare family/fallback, glyph shapes, wrapping and scaling in PNG inspection; scalar agreement does not certify font selection or shaping.
- `calibrationField(tester, actualFieldFinder)` exports both the outer wrapper and `InputDecorator.containerOf` bounds from the actual `EditableText` context. The latter is the border/fill container; matching an outer `SizedBox` proves neither. Inspect the painted border/fill, focused/error/disabled variants when supplied, padding and caret in their PNGs. Custom fields without that container need a measured adaptation and remain NOT VERIFIED in this helper.
- `calibrationBounds(actualCustomPaintRenderBox)` exports the real glow box. Include its actual scaffold/composition and at least one real overlapping consumer; export that consumer's bounds too. Compare both bounds with source composition, and inspect gradient extent/stops, opacity, clipping, tint and layer order against the skin's source PNG. A layer enum, color token or empty glow crop cannot prove composition. Unresolved source pseudo-element geometry remains NOT VERIFIED.
- `calibrationViewport(context)` reads runtime dimensions, DPR, locale, safe area and text scale. Export actual `context.tokens.skin.id`, `!debugDisableShadows` and `ScreenUtil().scaleWidth/scaleHeight`. Export the same `Size` variable actually passed as `designSize`, with its inspected scale policy; do not copy a declared profile as an observed viewport. An adapter without ScreenUtil needs a reviewed measurement adaptation; this helper does not assume one.

After the existing camera has saved its full PNG, add `capture: calibrationBinding(actualPngPath)` to each observation row and call `writeCalibrationExport(exportPath, runtimeInputPaths, rows)`. It hashes actual current files and directories and binds each exported row to the PNG. Include the executed probe, observation adapter, existing harness, actual core/theme/wrapper/skin files, pubspec/lock/package configuration, used fonts/assets/local packages and measured SDK/camera identity. Inspect those files and the exact successful command's complete log: the helper checks bindings, **it cannot prove execution or truthful measurements from JSON**. Never handwrite runtime observations to simulate an executed probe.

### Narrow manifest and evidence contract

A manifest has `schema_version: 1`, `inputs_complete: true`, nonempty `source_inputs` and `runtime_inputs` path lists, `capture: {command: [exact, argv], log: "complete-camera.log"}` and `rows`. Paths resolve relative to the manifest; directories are hashed recursively, including newly added files. Unknown dependencies prevent reuse; completeness is an inspected conclusion. Source inputs include original HTML/Figma materialization, all relevant resources, the source-capture probe and renderer identity. Keep outputs outside these inventories. Source and runtime export files and both camera PNGs are bound automatically, together with this adapter/helper, foundation extractor and comparator.

Each row has a unique slug `id`, `kind` (`typography`, `field`, `glow`), exact source `selector`, complete `profile`, `source_export` and `runtime_export`. Refresh actual SDK/browser identity before a reuse check; an old version file is not a current observation. The profile is the [source-cache profile](design-cache.md), plus `runtime_adapter`, `screenutil_design_size: {width, height}` and `crop: {x, y, width, height}` in viewport-relative logical pixels. Keep fonts, motion frame, pointer/focus and expected-state conditions explicit. Geometry checks allow at most one image pixel; typography checks allow 0.01 logical pixels, not a renderer-error allowance.

Both exports have `bindings: [{path, sha256}]` covering all corresponding current input files and `rows: {"row-id": {...}}`; binding/capture paths resolve relative to their export. Each source row has the exact `profile`, `capture: {path, sha256}` for the full source PNG and `facts` from the actual foundation snapshot, including `viewport`, `profile.skin`, `nodes` and `composition`. Each runtime row has the same profile as capture metadata, the bound full PNG, observed `viewport`, `skin`, `shadows_enabled` and `screenutil: {design_size, scale_width, scale_height}`. Metadata equality alone is not an observation.

Add the relevant runtime observations: `typography` from the render adapter; `outer_bounds` plus `painted_bounds` for fields; or `glow_bounds` plus `overlap_bounds: {"source-consumer-selector": measuredRect}` for glows. Rectangles use `{x, y, width, height}` in full-viewport coordinates. Glow manifest rows also name nonempty `overlap_selectors`; their source boxes must overlap the glow and fit inside the output crop. The helper reads source typography from `nodes[].computed`, fields from the selected node's `box`, and glows from `composition.visible[].bounds`. Unsupported/missing facts stop that row as NOT VERIFIED; a handwritten enum cannot replace them.

Open every source/actual/diff crop at full resolution, inspect runtime exports against the executed probe/core/harness and full logs, and record `inspection.json` with the attempt's `fingerprint`, `results_sha256` of the exact run report, nonblank `inspector`, overall `notes` and `rows: {"row-id": {accepted: true/false, notes: "measured findings"}}`. Inspect fields at their painted edges and glow overlap pixels in each supplied skin. Reject remaining fixable mismatches even on numeric PASS. `finalize` checks the fingerprint and all artifacts before writing a new report; it records an attestation, not automatic visual inspection. Use **CALIBRATED** only for accepted supported component rows, DIFF for rejected/differing rows and NOT VERIFIED for missing/unsupported checks.

`check` is read-only. It permits calibration reuse only when the original source/resources, working code, probe/core/harness/fonts, profiles, SDK/camera identity, logs, exports, captures, comparisons and inspected artifacts still fingerprint-match. A match with no accepted inspection is not reusable calibration. Any hit keeps `screen_verified: false`; capture and compare current required screens through the existing workflow. Changes or unproved dependencies require affected calibration again, never a borrowed screen PASS.
