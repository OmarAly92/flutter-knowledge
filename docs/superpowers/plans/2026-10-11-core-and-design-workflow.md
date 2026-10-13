# Core setup and design workflow implementation plan

> **For agentic workers:** Use executing-plans for the coordinated implementation and independent scoped workers for source extraction and the verification runner. No commits are authorized.

**Goal:** Add manual core setup and make the design workflow reach the reviewed quality with earlier diagnostics and repeatable evidence.

**Architecture:** Live convention skills remain the source of truth. `flutter-core` orchestrates initialization, contract inspection and core implementation. HTML extraction owns visible composition; visual verification owns attempts/comparison/inspection. Package defaults remain solely in flutter-init's catalog.

**Tech Stack:** Python, browser JavaScript, Flutter/Dart and the project-selected packages.

**Spec:** `docs/superpowers/specs/2026-10-11-core-and-design-workflow.md`

## Global constraints

- No authored code comments; no commits, releases or reference-app modifications.
- Preserve existing uncommitted changes and the reviewed fixture.
- Keep Drift/Hive separate and add neither as incidental core setup.
- Use context.tokens, existing naming/layering, configured mechanics and generated localization.
- Numerical comparison PASS requires separate PNG inspection; default settings are unchanged.

## Task 1: Manual core skill and inspection

Files: create `plugins/flutter-knowledge/skills/flutter-core/SKILL.md`, `references/core-contracts.md`, `scripts/inspect_core.py`, `evals/evals.json`, `tests/test_flutter_core.py`; update map, workflows and GEMINI includes.

- [x] Define invocation and auto-init handoff, partial-project preservation, required contracts and package adaptation.
- [x] Implement read-only JSON inspection of config, discovered/custom paths, required default contracts and startup/registration candidates. Presence is never a completeness certificate.
- [x] Test absent config, minimal core, partial/custom contracts, no writes, unknown selections and stable reruns.
- [x] Add skill-map/workflow/include entries; existing harness manifests continue pointing to skills directory.

## Task 2: Complete HTML composition extraction

Files: `html-to-widget/scripts/layout-tree.js`, `html-to-widget/references/source-extraction.md`, `tests/test_layout_tree.py`.

- [x] Preserve existing layoutTree API and output.
- [x] Add capture-boundary facts and visible outside-screen composition detection.
- [x] Reproduce a fixed app-shell handle missing from a screen subtree, plus hidden/clipped/decorative cases.
- [x] Record expected state, animation and pointer capture conditions in extraction guidance.

## Task 3: Verification runner

Files: `visual-verification/scripts/run_verification.py`, `visual-verification/references/runner.md`, `tests/test_verification_runner.py`.

- [x] Define versioned manifest with capture command, source-backed row IDs, references, current actual paths and controlled profiles.
- [x] Invoke Flutter test camera without shell interpolation; save complete logs and uniquely named attempt output.
- [x] Reuse compare.py --json with its defaults, preserving exits, dimensions and error semantics.
- [x] Produce results JSON, seven-column evidence Markdown and inspection-required statuses.
- [x] Finalize only through matching artifact hashes and explicit per-row inspection results, writing a separate reviewed report.
- [x] Test camera failures/stale output, immutable attempts, bad profiles, source identity, pass/diff/error parity and inspection refusal for changed artifacts.

## Task 4: Preflight and earlier behavior checks

Files: `golden-tests/references/capture.md`, `visual-verification/references/preflight.md`, visual-verification and source-reader/workflow handoffs.

- [x] Make calibration verify root/expected state, fonts, shadows, text wrapping/metrics, inputs, loading and source capture profile before the full screen matrix.
- [x] Put applicable async overlap, disposal and combined RTL/scale/narrow/keyboard checks before polish.
- [x] Use targeted correction runs and one final full gate after changes settle; retain every supplied state.

## Task 5: Minimal-project evaluation

Outputs: ignored task-owned evaluation directory separate from the reviewed fixture.

- [x] Prepare minimal Flutter source/pubspec without copied reference-app core or feature files.
- [x] Run skill-authoring paired evaluation for fresh core; test completing partial existing contracts and rerun preservation.
- [x] Independently analyze/exercise generated core APIs, DI, themes/registry/localization/wrappers and app-root startup.
- [x] Implement the same original HTML onboarding/setup/chat scope using generated core and new workflow/runner.
- [x] Compare every source-backed row and inspect responsive/RTL/keyboard variants; preserve initial and corrected outputs.

## Task 6: Final validation and presentation

- [x] Run affected repository tests and source-reference checks.
- [x] Review actual code, docs, manifests and skill links; all supported harnesses include the new skill.
- [x] Final Flutter gate owns whole-project analysis/tests; inspect source/capture/diff artifacts.
- [x] Produce skill-eval viewer, code/evidence links and source/Flutter image browser.
- [x] Report remaining checks, actual corrections and consumption evidence without treating cached token totals as billing or account limits.

## Execution evidence

Completed implementation and scoped evaluation. [Aggregate report](../../../benchmark/out/core-workflow-eval-20261011/evaluation-report.md) and [checkpoints](../../../benchmark/out/core-workflow-eval-20261011/progress.md) retain exact commands, failures, corrections and child IDs. Repository 88 tests and generic 24 / partial 25 / HTTP 22 gates pass. Fresh project 75 tests, formatting and strict analysis pass. Current 28-case camera and hash-bound inspection yield 21 VERIFIED, 1 deliberate light-setup2 DIFF and 6 source-less NOT VERIFIED; the design helper remains blocked by the disclosed accessible chip-spacing difference. The separate 96-run premerge benchmark did not run, version remains 2.5.0, and no commits/merges/releases/pushes occurred.
