# Adaptive state coverage and inspected baseline handoff

Read this when selecting state coverage or handing inspected candidates to ordinary golden regression. Source extraction stays with `html-to-widget` / `figma-to-widget`; profiles, numeric comparison, cache freshness and PNG inspection stay with the [verification runner](../../visual-verification/references/runner.md). These helpers validate evidence and promote files; they do not discover states, parse HTML, perform PNG inspection or replace the camera.

## Discover before declaring

Inspect the requested source through its existing reader and drive reachable controls at the intended profiles. Inspect the actual screen, state owner, listeners, validators and shared controls too. Follow transitions rather than accepting an initial screenshot or a declared inventory as coverage. Record locations and what was actually visited/read; unvisited source states remain unknown.

Consider the states the screen actually exposes: focus/caret, invalid/required/disabled fields, pending/loading, empty/data/error, selected/expanded tabs, sheets/dialogs/feedback, retry/completion/navigation, scroll and keyboard. Distinguish a visually different state from a nonvisual lifecycle assertion. Include shared consumers affected by changed controls. Keep a scoped discovery note with observed transitions, applicable states, exclusions and unresolved/unsupported states; hash it and the relevant code/source evidence in the ledger. An unsupported required state blocks completion rather than disappearing from a passing report.

For each applicable visual state:

- A supplied source variant gets a `kind: source` runner row with its original reference, explicit profile and fresh source/cache binding. Use the source reader to expose that state. It needs an inspected numeric PASS before baseline approval.
- A state without a supplied reference gets `kind: regression`, a controlled PNG and meaningful behavior checks. Record the absence of a reference; no synthetic source image or source VERIFIED claim. An accepted new regression candidate may have `comparison: NOT_RUN` because its first baseline does not exist yet.
- Retain the main state's supported matrix from [golden-tests](../SKILL.md#the-matrix). Other states get all supplied source profiles plus targeted risk variants: RTL/large text for field errors and feedback, narrow layouts for overlays, and actual focus/keyboard for forms. Include relevant combined RTL + large-text + narrow + keyboard checks. Select cases that expose changed layout/behavior, not a blind Cartesian product. Explicitly record unsupported requested cases and their reason. Do not drop overflow or keyboard failures.

A nonvisual state can use `required_behavior_tests` and a `behavior_only_reason` explaining why a PNG would not prove it. Visually distinct states require `required_rows`; behavior-only declarations do not excuse missing visual coverage. The helper checks declared coverage, not the completeness of discovery: the agent owns that inspection and attestation.

## Ledger v1

All evidence identities are `{"path": "/absolute/file", "sha256": "…"}` produced by the existing runner's `identity`. Keep relative baseline/test paths inside the app; evidence paths are absolute. Use stable row ids and exact Flutter machine test names (including group prefixes). Each manifest row belongs to one state and has a unique normal golden test name.

```json
{
  "schema_version": 1,
  "scope": "Auth UI refresh and affected field consumers",
  "manifest": {"path": "/evidence/manifest.json", "sha256": "…"},
  "project_snapshot": {"path": "/evidence/project-inputs.json", "sha256": "…"},
  "discovery": {
    "inspector": "implementation agent", "inspected_at": "2026-10-13T12:00:00Z",
    "notes": "Drove supplied variants; read owner transitions, listener and field validators.",
    "evidence": [{"path": "/evidence/discovery.md", "sha256": "…"}]
  },
  "states": [
    {"id": "auth-main", "evidence": [{"path": "/app/lib/auth_screen.dart", "sha256": "…"}],
     "required_rows": ["auth-main-dark", "auth-main-light", "auth-main-ar", "auth-main-text2x", "auth-main-narrow"]},
    {"id": "auth-error", "evidence": [{"path": "/app/lib/auth_screen.dart", "sha256": "…"}],
     "required_rows": ["auth-error"]},
    {"id": "owner-closed", "evidence": [{"path": "/app/lib/auth_cubit.dart", "sha256": "…"}],
     "required_rows": [], "required_behavior_tests": ["auth does not emit after close"],
     "behavior_only_reason": "Owner lifecycle has no surviving visible screen"}
  ],
  "rows": [
    {"id": "auth-error", "baseline": "test/feature/auth/goldens/auth_error.png",
     "golden_test": "auth error dark en", "behavior_tests": ["auth invalid email shows validation"]}
  ],
  "regression_tests": ["test/feature/auth/auth_golden_test.dart"]
}
```

The example abbreviates `rows`: the actual list must cover **every** manifest row. Missing/duplicate states, outputs, evidence, completed tests or reviews block. Declare unavailable states with `unsupported: "reason"`; this is a blocker, never a waiver or PASS. `scope` limits the claim; a minimal exercise ledger cannot certify the full app. Do not edit a ledger after failure to make required coverage disappear.

## Capture and behavior

Resolve the supplied source rows first with the focused manifest, then capture the regression matrix in the one complete run ([source rows first](../../visual-verification/references/runner.md#source-rows-first-complete-gate-second)). Create no baseline PNG for a row that is blocked by [capture readiness](capture.md#capture-readiness), uninspected, DIFF/ERROR or part of a ledger whose coverage is BLOCKED: no `--update-goldens` output at an approved path and no copied candidate. Leave candidates in attempt evidence and report `baseline_approval: BLOCKED`. Approved baselines already in the project stay unchanged until the handoff promotes inspected replacements.

Before the candidate capture, save an input snapshot:

```bash
python3 "<golden-tests>/scripts/state_coverage.py" snapshot --project <app> > <evidence>/project-inputs.json
```

It hashes app source, authored Dart tests (including the existing camera/harness), assets/fonts, local `packages/`, pubspec/lock, project config, test tags and installed package configuration. It is a file snapshot, not a code/source parser or state inventory. External dependencies remain bound by the package configuration/lock; hash extra external inputs in discovery evidence when they affect this task. The snapshot must precede the runner capture and still match at review/promotion. New, edited or deleted code/assets invalidate it. Cache exclusions are limited to the app root (outside the scanned source folders) and `build/`, `.git/` or `.dart_tool/` directly under a local `packages/` root identified by its `pubspec.yaml`; its `.git` worktree pointer file is also excluded. Nested authored paths such as `lib/feature/build/`, `assets/build/`, `packages/local/lib/build/` and `test/feature/build/` remain tracked, including authored nested `.git`/`.dart_tool` names. The app’s `.dart_tool/package_config.json` remains explicitly tracked. Baseline PNGs/metadata and failure images are excluded so promotion can change them; custom captures must bind any test-side asset inputs in discovery evidence.

Run the existing runner with its unchanged CLI and fill its inspection template **after opening the actual candidate PNGs**, plus reference/diff where supplied. Its `finalize` can retain the source report; the ledger checker reuses `validate_inspection` and derives statuses from the original results, not caller-authored `reviewed.status` strings. A checkbox or metadata alone proves no visual inspection. Preserve all earlier attempts.

Record real behavior tests with the trusted installed Flutter executable, using structured test file paths:

```bash
python3 "<golden-tests>/scripts/golden_handoff.py" behavior --project <app> --flutter <installed-flutter> --test test/feature/auth/auth_behavior_test.dart --out <evidence>/behavior
python3 "<golden-tests>/scripts/state_coverage.py" check --ledger <ledger.json> --results <attempt>/results.json --inspection <inspection.json> --behavior <evidence>/behavior/tests.json
```

The behavior helper retains fixed argv, exit, full stdout/stderr, hashes and project inputs before/after the run. It parses Flutter `--machine` events; successful exit, a claimed PASS string, hidden framework loaders or skipped/empty suites do not qualify. Successful completions must explicitly report `hidden: false`; real tests named “loading …” qualify normally. Every required named test must finish successfully. Behavior tests must drive the relevant transitions/assertions, including automatic keyboard avoidance when claimed; seeded state or forced `ensureVisible` is insufficient.

Use one camera that chooses the existing candidate path from `CAPTURE_ROUND` during capture and the declared approved path when that define is absent. Normal mode must execute the same named state tests with `matchesGoldenFile`; no skip-by-default capture suite, no update flag, no test that merely exists. Assert expected state/root and profile conditions before the PNG is taken, as in [capture.md](capture.md).

## Promote, check, recover

User-authorized UI work permits the implementing agent to inspect and approve local baselines. No extra user confirmation is needed for that local handoff; publication/commits remain outside this helper.

```bash
python3 "<golden-tests>/scripts/golden_handoff.py" promote --ledger <ledger.json> --results <attempt>/results.json --inspection <inspection.json> --behavior <evidence>/behavior/tests.json --flutter <installed-flutter> --out <evidence>/promotion
python3 "<golden-tests>/scripts/golden_handoff.py" resume --out <evidence>/promotion --flutter <installed-flutter>
python3 "<golden-tests>/scripts/golden_handoff.py" rollback --out <evidence>/promotion
```

Promotion first validates the whole ledger, unchanged camera/source/reference/profile/candidate/log identities, the runner's actual inspection, source freshness and passing behavior evidence. It refuses DIFF/ERROR, rejected/uninspected/missing states, or source rows that are not VERIFIED. Regression-only rows can be approved without a design reference, but remain NOT VERIFIED for source fidelity.

A new transaction stages candidates and exact profile bytes, backs up each previous baseline plus its `.profile.json` and `.approval.json` sidecars, retains the prior review identity and copies of the validated input records, and writes `transaction.json` before changing baselines. Evidence and candidates remain unchanged. The helper copies the inspected PNG to its declared ordinary baseline and stores profile/review sidecars. It immediately runs:

```text
<installed-flutter> test --no-pub --machine <declared test/*_test.dart files>
```

There is **no** `--update-goldens` or `CAPTURE_ROUND`. No arbitrary manifest argv is executed. Keep complete check logs and the actual machine result; every declared row's named golden test must complete. Failure rolls back the old PNG/profile/review (or removes a newly introduced baseline) and reports normal regression FAIL. A zero exit from an empty/skipped/unrelated suite also rolls back. The executable is a trusted caller-selected installed Flutter path, never taken from the ledger.

Resume revalidates evidence, project inputs and target hashes; interrupted writes/checks continue without reusing a previous attempt's PNG or overwriting old logs. Rollback validates target confinement, the recorded replacement hashes and intact original backup identities, refuses external edits, and restores preserved bytes even when staged replacement files are missing or changed; interrupted rollback can be resumed. It atomically writes `baseline_approval: ROLLING_BACK` before restoring any target, then `ROLLED_BACK` after restoration. Recovery resume persists the revocation again before continuing; restoration never leaves this transaction’s durable `handoff.json` marked APPROVED. Missing or changed original backups block restoration. A rejected rollback records BLOCKED in the durable handoff and leaves target bytes untouched. An interrupted check gets a new numbered log directory. If inputs changed, resume blocks and rollback remains available. `APPROVED` resume checks the retained successful regression evidence and baseline identities again; do not launder old acceptance after changes. Staging failure before the journal leaves original baselines intact: inspect/retain that failed transaction directory and start a new output directory.

Keep four separate report axes: `source_fidelity` per row (VERIFIED/DIFF/NOT VERIFIED), `baseline_approval` (ELIGIBLE before handoff; APPROVED/BLOCKED/ROLLING_BACK/ROLLED_BACK after it), `behavior` (PASS/FAIL), and `normal_regression` (NOT_RUN/PASS/FAIL). `coverage: COMPLETE` means the declared scoped requirements have evidence, not that unvisited states were discovered or that every source screen is verified. `handoff.json`, original runner results/review, transaction backups and numbered check logs together form the handoff evidence. Normal regression describes the retained candidate-baseline check; manual rollback retains that historical result and does not approve or certify the restored baseline. Unavailable or invalid historical check evidence is reported as FAIL while restoration can still proceed from valid backups. Evidence becoming stale during an otherwise passing check revokes promotion separately and records `current_coverage`/`approval_issues`.
