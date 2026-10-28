---
name: flutter-review
description: Use for findings-only Flutter reviews and readiness checks before handoff, commit or PR; inspect conventions, formatting, analysis, tests and existing evidence without fixing or recapturing.
allowed-tools: Read, Grep, Glob, Bash
---

# Read-only Flutter review

Review and report. Do not fix files, create config, install dependencies, run generators, launch the app or update golden baselines during this skill. Initialization is a separate action; a missing/unresolved config is reported. Package choices never suspend the convention checks.

The [task workflow](../flutter-knowledge/references/workflows.md) owns what happens after findings: implementation tasks can return to implementation for fixes; review-only tasks end with findings. This skill and its helper remain read-only in either case.

## Mechanical checks

Resolve the helper from this skill's path and run:

```bash
python3 "<skill-directory>/scripts/review.py" --project "<flutter-project>"
```

The helper requires Python/PyYAML and the local Dart/Flutter tools. It reads `flutter-knowledge.yaml`, includes staged, unstaged and untracked app-relative Dart paths, and excludes recognized generated files. When Git knows none of the app's `lib`/`test` Dart files (not a repository, or an app ignored by an enclosing one), the scope falls back to all authored files; a clean tracked app stays changed-only. For changed work, confirm the reported scope is non-empty and covers the files you changed; a 0-file scope is unreviewed, not clean. `--all` examines all authored files; `--skip-tests` is an explicit quick-review choice, reported as skipped; `--json` emits structured findings. `--log-dir <path>` retains complete output in a new report-only subdirectory and emits concise failure details with log paths. This optional argument authorizes those evidence logs; source/config/baselines remain unchanged. Read full logs whenever summaries are insufficient, accounting for every failure. Timeout logs retain partial output and are marked incomplete; a timeout remains a could-not-complete result, never a pass.

Formatting uses `dart format --output=none --set-exit-if-changed`. Analysis and Flutter tests use `--no-pub`; the script does not fetch packages or run `--update-goldens`. The verified automated runner is Flutter's test runner. An unsupported selected runner is reported rather than silently replaced. Analysis/testing may produce normal tool cache artifacts; source and baselines are never intentionally rewritten. Test code can have arbitrary side effects: do not run untrusted tests or tests known to mutate source without inspecting/scoping them first.

Exit codes: `0` mechanical checks completed without blocking findings; `1` blocking findings; `2` a required check could not complete. A skipped or manual check is not a pass. Return code 0 does not certify the manual architectural review.

## Final batch ownership

During implementation use focused checks. Once changes settle, this gate runs required analysis/full tests; do not duplicate that suite immediately before invoking it. Project requirements take precedence. Subsequent source/dependency changes invalidate relevant checks and require another run. --skip-tests always means skipped; it never turns prior results into a current automatic pass or satisfies a required final suite by itself. Keep manual review unchanged.

## Configuration blockers and independent checks

The helper currently exits early when config is missing, malformed or contains any unresolved category. Report that limitation; it does not justify initializing config during review or blocking unrelated implementation. If it exits before checks run, continue independent read-only inspection and, when available, `dart format --output=none --set-exit-if-changed <scoped-files>` and `flutter analyze --no-pub --fatal-infos`. Inspect existing design evidence and applicable conventions manually. Run tests only when the selected runner is established and the tests are safe to execute. Keep package-dependent checks unavailable where their selection is unresolved, record every command actually run, and retain the helper failure in the final report. Do not present fallback checks as a clean helper run.

## Read the diff and the contracts

Read [the review checklist](references/checklist.md) alongside the task skills and project config. Confirm state naming/data ownership, route composition, data boundaries, reuse by role, responsive/accessibility behavior and the reason for each dependency or changed golden.

The helper reports definite production print/token and missing/undeclared literal assets, plus context-dependent token and duplication findings. It also flags likely state-owner/file naming issues, misplaced presentation files (extra `presentation/` dirs, loose `logic/` files, data classes in `logic/helpers/`), fields in success states, provisioning inside Screen files, missing Body composition, effects near builder callbacks, post-await owner logic and controller lifetime for manual inspection. These are lexical candidates, not a Dart AST or control-flow proof; aliases, callbacks and custom backends require manual review.

Localization checks flag likely literal UI text and physical directional layout for review. For the default easy_localization catalog locations, changed English/Arabic JSON files (or `--all`) get a leaf-key parity check; alternate catalog locations and localization backends remain manual. Dependency checks name added/changed packages against HEAD and flag catalog families different from the selected config. A declaration may be transitional or serve another category, so package findings never automatically change YAML or install/remove anything. Regex/source inspection is a lead to review, not permission to mechanically change code. Preserve the older-theme exception defined by the existing theme/map/UI skills; do not migrate a project to clear an audit.

## Design-driven work

Establish the complete screen/state/variant coverage from the implementation request and the [visual-verification contract](../visual-verification/SKILL.md#required-completion-contract). For design-driven work, pass every required source-backed row label explicitly; do not infer the coverage solely from the report, which may omit a screen:

```bash
python3 "<skill-directory>/scripts/review.py" --project "<flutter-project>" \
  --design-screen "Login / loaded" \
  --design-screen "Checkout / loaded"
```

Use `--design-report <path>` when the Markdown evidence file differs from `docs/design/verification.md`. The path is relative to the Flutter project unless absolute. Each `--design-screen` must exactly match the first cell of one row in the seven-column table defined by visual-verification. Avoid Markdown emphasis or pipes in row identifiers. The reference cell links one local reference PNG (alongside source identity); the capture cell links the Flutter PNG first and diff PNG second. Links resolve relative to the report. Overall and worst-region cells contain plain percentages such as `1.24%`. Capture profile and status must be present.

Missing/duplicate rows, missing/empty or reused artifact paths, invalid percentages, and statuses other than VERIFIED block the design-evidence check. Existing evidence is **manual**, never automatically verified: inspect actual image contents/dimensions, source identity, capture profile, freshness, comparison command/output/settings and any residual differences. The helper neither decodes the images nor recomputes reported percentages, and never captures or regenerates anything. Without explicit design scope, it reports this check skipped; establish whether that is appropriate from the task. Pure nonvisual work needs no screenshot report.

## Report

Lead with blocking findings, then review-required observations, then checks performed/skipped. Each finding needs path/line evidence, the concrete consequence and a suggested correction. Separate tested facts from manual judgement. If the checks are clear, say so without manufacturing issues. Fixes happen only in a separately authorized implementation step.

JSON includes `completion` (`blocked`, `could_not_complete`, or `manual_review_required`) and `design_results` with the reported percentages and artifact paths. Return code 0 still leaves manual review pending. The final agent report separates blocking findings, review-required candidates, checks actually verified and checks not performed; never promote evidence presence or an unchecked manual item to VERIFIED.
