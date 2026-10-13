# Task workflows

This reference owns task routing, handoffs and the final completion report. The skill map owns conventions and each specialist owns its detailed instructions. Read the applicable route once per task; direct specialist invocation uses the same route without recursively restarting the map. Load only specialists needed by the requested changes.

## Establish scope and configuration

Identify the requested outcome: explanation, planning, implementation, initialization, tests or review. Preserve explicit source paths, screen/feature scope and project constraints. Do not turn planning into implementation or a local fix into whole-app redesign.

Read existing configuration once when package mechanics matter, then inspect relevant installed APIs and project contracts. Reuse those decisions across skill handoffs; reread only when configuration/dependencies change or a new category becomes relevant. Follow the [configuration contract](../../flutter-init/references/configuration.md). During authorized implementation, invoke `flutter-init` if configuration is absent. Planning, explanation and findings-only review never create or refresh it implicitly. Missing config in those modes is an assumption or finding, not permission to write it.

An unresolved package blocks only changes dependent on that choice. Continue independent work and record the unresolved category. For review, the helper may stop early on configuration issues; use `flutter-review`'s independent read-only fallback and report the incomplete checks. Never pick a competing backend by majority usage or disable a convention. Configuration defaults are selections, not instructions to install packages.

## Efficient execution without weaker checks

Use one agent for ordinary screen/feature work. Additional agents are for explicitly requested reviews, genuinely independent larger tasks or required skill-authoring/benchmark validation. Do not create a second worker merely to reread the same source or rerun the same checks.

Load the map/route and relevant specialists once, retaining decisions through handoffs. Read specific files and extracted facts, not entire repositories, giant escaped HTML payloads or complete passing-test logs. Reuse source inputs through the [validated cache contract](../../visual-verification/references/design-cache.md); changed source/assets/profile/renderer invalidate reuse. Reuse an existing capture harness and add the task's needed cases; do not build another harness or install absent default packages.

Resolve unmatched source values before implementation through the [early design decision](../../flutter-app-theme/SKILL.md#early-design-decision). Exact-source authorization uses the existing source-of-truth rule. Scale-preserving work discloses mappings and the likely fidelity gap; unresolved conflicts get one concrete bundled question while independent work continues. Do not spend visual rounds trying to fix a deliberately different mapping.

Before the full capture matrix, run the [core and capture preflight](../../visual-verification/references/preflight.md), and run the applicable pending-operation/disposal and combined Arabic/large-text/narrow/keyboard checks before visual polish. For multi-row design work use the [verification runner](../../visual-verification/references/runner.md), correct with targeted rows and keep one complete final run.

During fixes, run relevant focused tests/captures. The final flutter-review invocation owns required whole-project analysis/tests once the batch settles; do not duplicate that suite immediately before the gate. Baseline checks and more frequent project requirements remain required. New changes/failures after the gate trigger relevant checks again. No old result or cache hit substitutes for validating changed code.

Keep full command output in local evidence logs; give the agent summaries, exact failed cases and artifact paths. Use comparison JSON for machine-readable evidence, preserving exits/settings, then inspect PNGs. A contact sheet is triage of all required changed variants, not permission to omit any. Open full-resolution images wherever labels, geometry, state, direction or differences are uncertain. Unresolved inspection cannot become VERIFIED. No required variants, behavior/accessibility checks, comparisons or manual review items are removed for efficiency.

## Select the route

| Request | Lead and sequence | Completion |
| --- | --- | --- |
| Explain code or discuss architecture | Map → relevant convention references → answer grounded in the project | Explanation; no initialization, app changes or automatic test runs |
| Initialize/refresh selections | `flutter-init` | Config, detected/recommended choices and unresolved categories; no implementation |
| Plan a whole app from HTML/Figma | Matching source reader → existing foundation inspection → [design briefs](design-briefs.md) | Source inventory, proposed foundations, screen briefs and planned verification coverage; no Dart/theme edits or SDK prerequisite |
| Implement a screen/component from HTML/Figma | Matching source reader (complete visible composition) → relevant implementation skills → core/capture preflight → earlier behavior checks → `visual-verification` → `flutter-review` | Built scope plus per-screen comparison evidence and final report |
| Implement an entire app or multi-screen feature from a design | Matching source reader → briefs where needed → implement and verify each screen → final `flutter-review` | Every requested screen accounted for, including blocked/unverified ones; do not stop at briefs |
| Apply complete foundations/assets from a whole HTML design (`/set-theme-from-html`) | Existing `/flutter-core` → `set-theme-from-html` using shared HTML extraction → `flutter-app-theme`/owning UI skills → targeted source-backed foundation/component verification → `flutter-review` | Applied seven-group theme, original asset/font imports, role mappings and honest foundation evidence; later `/html-to-widget` implements screens |
| Implement design foundations | Source reader → `flutter-app-theme` and relevant shared-widget conventions → verify affected in-scope reference-backed screens → `flutter-review` | Requested tokens/theme/components and their verification; no unrelated screen rewrite |
| Bootstrap or complete shared core (user invokes `/flutter-core`) | `flutter-init` when config is absent → `flutter-core` inspection and owning convention skills → core/capture preflight → `flutter-review` | Created/completed/preserved core components, selected mechanics, missing project decisions and executed checks; never a side effect of screen work |
| Implement/fix code without a design | Relevant convention skills → scoped implementation → existing affected tests and analysis → `flutter-review` | Correct requested behavior and honest checks; no invented screenshot reference |
| Write unit tests | `flutter-testing` plus conventions for code under test → run focused tests → `flutter-review` | Requested meaningful coverage and outcomes |
| Add/debug golden regression tests | `golden-tests` → run relevant tests → `flutter-review` | Reviewed baselines/failures; source fidelity only if a source comparison also ran |
| Review only | `flutter-review` → mechanical checks and manual inspection | Findings only; no config creation, fixes, installs, captures or baseline updates |

HTML screen/planning sources belong to `html-to-widget`; `set-theme-from-html` applies whole-design foundations after core, sharing the same extraction reference. Figma sources belong to `figma-to-widget`. If a source/tool is unavailable, report the specific missing input and continue work that does not depend on it. Never claim extraction or visual comparison occurred without evidence.

## Responsibility boundaries

- **`flutter-knowledge`:** select scope/route, retain configuration decisions and assemble the final report. It does not repeat specialist recipes.
- **`flutter-init`:** config schema, defaults, discovery and initialization. Its observations do not redefine conventions.
- **Implementation skills:** feature placement, UI/state/data contracts, routing/DI, themes, localization and storage. Invoke only those touched. Accessibility/responsiveness/performance add their scoped responsibilities.
- **Source readers:** inspect source values, geometry, assets, states and interactions; produce source facts for briefs or implementation. Theme decisions belong to `flutter-app-theme`, not a second token policy in the reader.
- **`set-theme-from-html`:** orchestrates whole-HTML foundation application and original asset import after core; shared HTML extraction and `flutter-app-theme` remain the source/value and token API owners. Its component captures establish only the checked foundation scope, never complete app/screen fidelity.
- **`flutter-core`:** manual-only shared core creation/completion through the owning convention skills. It never bootstraps core during ordinary screen work; when core is missing, report it or ask the user to run it.
- **`visual-verification`:** coverage, matching source/Flutter profiles, comparison commands, diff inspection, fix loop and evidence report. It calls the shared golden capture reference; fixing stays part of implementation, outside findings-only review.
- **`golden-tests`:** shared capture harness and regression baselines/variants. Capture alone is not design approval. Return capture artifacts to visual verification when it called this skill; do not restart the source-reader workflow.
- **`flutter-review`:** findings-only final gate. It consumes existing evidence and returns gaps; it does not create evidence or certify uninspected images.

## Handoffs and correction loop

Carry the task scope, relevant config selections, source/frame/state identities, affected files, unresolved decisions and verification coverage through each handoff. These can remain in working context; do not create a separate process document for a small task. Multi-screen planning uses the screen briefs as the durable handoff.

Run review after implementing and verifying the requested scope. If implementation was authorized, return actionable review findings to the responsible implementation skill, fix them, then rerun affected checks. Do not make the review helper write changes. A review-only request ends with findings; a capture blocker or missing decision is reported explicitly without relabeling the task as verified.

## One final completion report

Report the implemented/planned scope, files/artifacts, checks actually run and their outcomes, unresolved findings and checks not performed. For design work include each screen/state's status and measured overall/worst-region difference, linking the canonical evidence report owned by `visual-verification`. For planning, link briefs and distinguish proposed from existing foundations; do not fabricate percentages. Review exit 0 means mechanical checks had no blockers, not that manual checks passed. Do not claim full completion while required work remains.

No workflow authorizes committing, publishing or installing every recommended package as an automatic final step.
