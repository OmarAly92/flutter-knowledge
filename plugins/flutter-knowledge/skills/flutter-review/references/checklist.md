# Manual review contract

Review against the selected packages and these skills' fixed conventions. Observed project patterns do not authorize changing the prescribed architecture.

- State: keep XCubit/XState/file naming and per-operation variants, owner-held nullable models and payload-free success. Check cleanup, initial-fetch timing, post-await liveness and operation-specific concurrency behavior. Never substitute model-bearing AsyncValue merely because Riverpod offers it.

The helper blocks `identityHashCode(this)` in state `props` or `hashCode` getters:
instance identity cannot replace field-based equality. Other equality overrides
and repeated UI-operation transitions still require manual inspection.
- Composition: Screen effects, content-only Body, selective rebuilding and route-owned provider/owner lifetime. No extra owner in the Screen, stale callbacks after disposal, or effects inside a render builder.
- Data: nullable model fields, per-method Params, authored member order, API/result/failure boundaries and configured storage mapping. Transport or storage types must not leak into presentation.
- Reuse/assets: search live by role in discovered shared and feature locations; read the existing component API. Validate actual assets/declarations, including generated constants and dynamic paths the helper cannot prove.
- UI: apply accessibility/RTL and responsive skills to the changed interaction, including combined variants where relevant. A small-screen screenshot alone does not establish focus or screen-reader behavior.
- Performance: distinguish justified structural improvements from profiled results. Confirm caching/boundary/row-height changes preserve behavior.
- Tests: inspect meaningful success/failure coverage and state sequences where tests are requested or already cover the change. Respect the existing DI-registration and design-golden exceptions; do not generate extra suites as a review action.
- Goldens: inspect all changed/new PNGs and explain intentional baseline differences. Never approve regeneration just because the test becomes green.
- Scope: include app-relative tracked and untracked files, generated exclusions and package/config changes. Configuration/library declarations are not proof of active usage or API version compatibility.

No strictness/profile option downgrades or disables the conventions. Package mechanics may vary; the architectural responsibilities stay fixed.

- Design fidelity: for design-driven UI, inspect the [per-screen verification evidence](../../visual-verification/SKILL.md#required-completion-contract): complete in-scope coverage, original source references, matching capture profiles, Flutter and diff artifacts, overall/worst-region percentages and honest statuses. Missing evidence or unresolved differences prevent a verified-design claim even when mechanical checks pass. Review remains findings-only: report gaps without capturing, regenerating baselines or rewriting the report.

- Automation limits: resolve every lexical candidate against the real Dart structure. Validate missing detections manually for aliases/custom backends; zero candidates is not proof of convention compliance. Establish design scope from the task, pass all required rows to the helper, and inspect artifact contents/freshness and comparison output before certifying fidelity.

Existing asset directories assigned to constants remain manual prefix checks, including prefixes without a trailing slash. A directory passed directly as a literal image asset still fails the file-existence check. Resolve the final composed filenames and their declarations during inspection.
