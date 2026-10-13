# Project configuration contract

Before writing package-dependent code, read `<project>/flutter-knowledge.yaml`. During authorized implementation, if absent invoke `flutter-init`; initialization itself does not require an existing config. Planning, explanation and findings-only review do not initialize or refresh configuration implicitly. Reuse relevant selections through the task and reread when they change. Unresolved categories block only their dependent implementation; continue independent work and report ambiguity. Malformed configuration must be reported rather than treated as a valid selection. Read the current `pubspec.yaml` and relevant lockfile/package source as well: a config selection is not evidence that a dependency is installed or that an API exists in its version.

The config has `schema_version: 1`, a `packages` mapping, and derived `resolution` metadata. Each `packages.<category>` value is a package name, the built-in strategies `navigator` (routing only) / `manual` (serialization only), the explicit choice `none`, or unresolved `null`. Categories and recommended defaults live only in [package-catalog.json](../package-catalog.json). Use the initializer to materialize the current defaults rather than duplicating them in another template.

- `resolution.<category>.source`: `pubspec`, `recommended`, `configured`, `builtin`, or `ambiguous`.
- `declared`: whether the selected name appears directly in pubspec. It does not mean dependencies have been fetched.
- `section`: the dependency section for a declared package.
- `candidates`: alternative detected choices when selection is ambiguous.
- `used_in`: authored source paths supporting the selected package family, when observed. These are evidence, not proof of runtime reachability.
- Unknown package categories are rejected to catch spelling errors. Unknown top-level keys are retained. `project_contracts` may identify existing API, result, theme or wrapper files; inspect the files rather than inferring their signatures from names.

Existing non-null package selections win on rerun. Remove a category or set it to `null` to detect it again. Unknown packages may be selected explicitly; the initializer reports them for API verification. Companion names in one catalog family use the same implementation guidance (for example `hive_ce_flutter` selects the Hive CE guidance). The recognition catalog is detection support, not a claim that every combination has a tested implementation template.

## Discovery

`discovery` is refreshed from authored source and pubspec. It contains shared widget/component locations, candidate custom-contract paths, observed screen/page and widget-prefix counts, import-style counts, asset declarations and state-backend evidence. Generated code, comments and string examples do not vote for a backend. State implementation markers provide stronger evidence than an import alone; other import evidence still needs human/API inspection. A single observed family can resolve fresh declaration ambiguity, while explicit selections remain unchanged and several live stacks require a choice.

Discovery is descriptive. A project full of Page classes does not change the prescribed Screen/file naming. A legacy token or architecture pattern does not override the three existing older-theme notes or the fixed layer responsibilities. Store locations and search live by role; do not trust a saved inventory of components. Multiple matching contract files stay candidates rather than choosing one arbitrarily. Existing project_contracts selections win.

## Precedence and scope

1. Follow explicit user/project constraints and this plugin's architectural conventions.
2. Use the config to choose package mechanics. An alternative selection overrides literal package imports/API calls in the default examples, but never their architectural contract.
3. Verify the selected mechanism against actual project source and its installed package API. If it cannot express the required convention, report the precise conflict before dependent changes. Never quietly replace the convention with that package's usual tutorial architecture.

Recommended but missing dependencies are not permission to install everything. Add a selected dependency only when the current task needs it and the user's scope permits it. A detected code generator can be used; a default selection does not revoke the rule against adding code generation incidentally. `none` means do not add that mechanism; it does not disable the architectural responsibility it would implement.

Custom APIs such as `ApiConsumer`, `GlobalResponse`, `Failure`, `AppTokens`, `AppText` and navigation extensions are project contracts, not packages. Preserve their behavior and layer ownership. Mirror the existing contract where the skill permits it; do not invent missing wrappers or migrate an older theme as a side effect.

## Applying a skill

All package-specific imports, method names, generators and harness examples in the skills describe the default stack unless explicitly scoped otherwise. Read [package adaptation](package-adaptation.md) for the selected category. Load only the needed category guidance, and keep the named skill's conventions as the authority. In the default Bloc family, use Cubit rather than event-based Bloc.

The baseline invariants remain: feature-first folders; Screen/Body split; route/composition-owned state provisioning; method-specific `...State` names; owner-held nullable data with payload-free success states; lifecycle-owned controllers; model/params naming and nullability; repository boundaries and failure semantics; shared visual tokens; complete English/Arabic translations; and the existing test/design policies. Package selection does not make these optional.
