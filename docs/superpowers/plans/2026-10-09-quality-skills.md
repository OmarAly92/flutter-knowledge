# Discovery and Flutter quality skills implementation plan

Goal: add source-based discovery, concrete state references and four quality skills without allowing package configuration to weaken architectural conventions.

## Fixed boundaries

Keep XCubit/XState and operation State names, owner-held nullable data, payload-free success, controller ownership, initial fetch in owner creation, route-owned provisioning, Screen/Body composition, nullable models, per-method params, token policy and both database skills. Discovery records observations rather than replacing these rules.

## Deliverables

1. Extend flutter-init with comment/string-aware source evidence, contract locations, declared asset locations and observed naming. Preserve user selections; use decisive source evidence to resolve declared alternatives without majority voting. Store locations and evidence, not a widget inventory.
2. Add verified Riverpod and Provider references and strengthen the shared async-lifecycle rule. Retain the Cubit reference; version-scope other backends instead of claiming arbitrary APIs are validated.
3. Add flutter-accessibility-rtl, flutter-responsive-layout, flutter-performance and flutter-review. Keep skill triggers scoped and package-independent principles explicit.
4. Implement a read-only review helper: app-relative Git scope including untracked files, generated exclusions, formatter check without output writes, analysis without pub fetching, selected existing tests, asset/token checks and manual review notes.
5. Wire the map/Gemini/docs and refresh both diagrams. Validate behavior, package examples, unchanged convention invariants, distribution and all relevant suites. Full pre-merge benchmark remains required before integration.
