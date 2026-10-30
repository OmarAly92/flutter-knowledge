---
name: flutter-core
description: Use when creating/completing shared Flutter core, explicitly or through implementation readiness; full foundation for fresh apps, only required gaps in existing apps. Planning/review never bootstrap core.
---

# Create or complete Flutter core

`/flutter-core [project-path]`

Resolve an optional project path from the invocation; otherwise use the current Flutter project. Verify its `pubspec.yaml`. Follow the [core readiness gate](../flutter-knowledge/references/workflows.md#core-readiness-during-implementation) to select full bootstrap/completion or task-scoped dependency completion. Direct `/flutter-core` defaults to the full foundation unless the user limits its scope. An automatic existing-app handoff never authorizes the whole inventory. Preserve existing behavior and package choices. No business features, authentication policy, backend URLs, database schema or unrelated toolkit installation are implied. Required core APIs and supplied-local-package contracts live in [core contracts](references/core-contracts.md#core-api-alignment).

Keep the caller's origin, selected responsibilities and return task in working context. All creation, registration, startup, package/native setup and verification instructions below apply only to that scope and its necessary dependencies. A scoped cache helper does not authorize adding a router, theme, root network owner or unrelated secure storage. Load only its owning skills/reference sections; do not recursively invoke core through their workflow entry points.

## Initialize first

Read [the configuration contract](../flutter-init/references/configuration.md). If `flutter-knowledge.yaml` is absent, invoke `flutter-init` and run its initializer before package-dependent core work. Calling this skill before `/flutter-init` is supported. Check an existing config; when catalog categories are missing, rerun the initializer to fill them while preserving explicit choices. Unresolved choices block only their dependent components. Defaults live exclusively in the initializer's catalog.

## Inspect and plan the completion

Run the read-only helper:

```bash
python3 "<skill-directory>/scripts/inspect_core.py" --project "<flutter-project>" --json
```

It reports contract evidence, missing conventional files, configured paths and package adaptations. It does not generate code or certify completeness. Inspect actual implementations and callers, not just filenames or class presence. Use config discovery to find existing equivalents; do not create a parallel API/theme/router when a custom contract already fulfills the role. The helper's [contract inventory](references/core-contracts.json) is a transient inspection aid, not a saved component inventory in project configuration.

For scoped completion, retain full inspector output locally and read the relevant contract rows/configuration instead of loading the entire missing-file checklist into context. Reuse that inspection across handoffs.

Make a short missing/incomplete/preserved table for the selected responsibilities, state the automatic scope briefly and implement the necessary gaps without an extra permission round. Missing inspector rows outside scope are observations, not required work. Reuse working equivalents and preserve custom routes, registrations, constructors, theme values, assets/fonts, locales, cache keys and startup effects. A rerun should add no duplicate registrations, providers, translations or declarations. Follow the existing theme architecture decision in `flutter-app-theme`; core setup is not permission for an unrequested migration.

## Build the essentials

Read [core contracts and startup](references/core-contracts.md). Apply the owning skills before implementation:

- `flutter-feature-structure`: core locations and existing equivalents.
- `flutter-routing-di`: router library/parts, typed core registrations and app dependency entry.
- `flutter-data-layer`: consumer, endpoints, GlobalResponse, Result/Failure and error boundaries.
- `flutter-state-management`: root state owners, fields, equality and disposal.
- `flutter-app-theme`: all seven token groups, skins, registry, selection and ThemeData mapping.
- `flutter-screen-ui`, `flutter-accessibility-rtl`, `flutter-responsive-layout`: shared wrappers, direction extensions, semantics and constraints.
- `add-translation`: required English/Arabic keys and generated accessors for the selected localization backend.

For full bootstrap/completion, create the requested foundation: routing/DI; theme/tokens/skins/loading; API/error handling; network; layout; localization/preferences/logger; principal text/scaffold/appbar/container/spaces/button/field/sheet/feedback wrappers; app-root wiring. For a scoped handoff, complete only the selected contracts and the dependencies/registrations that make them usable. Narrow the set of services, not a selected service's standard public contract to just the values in one fixture. Missing unrelated services do not expand scope. A needed API class left unregistered or a newly required AppTokens extension absent from ThemeData is incomplete selected work.

Full foundation work includes both ordinary and secure cache through [cache storage](references/core-contracts.md#cache-storage); scoped completion creates only the needed cache contract. Sensitive values use `SecureCacheHelper`/`SecureCacheKeys`; ordinary preferences stay in `CacheHelper`/`CacheKeys`. Apply the selected secure backend and await initialization when sensitive persistence is in scope. This does not authorize inventing authentication features.

The default recipes follow the reference architecture, not its application features. Use target package imports from pubspec's `name`. Selected alternative packages keep the same responsibilities, naming and lifetimes through their verified APIs. Read only applicable package-adaptation sections. Never switch an alternative to a default just to match a recipe.

Before authoring a missing or incomplete cache, HTTP logger or component mapping, read only its matching [tested reference implementation](references/reference-implementations.md). Adapt verified mechanics to the target contracts; do not replace working implementations or change package versions to fit a reference.

Add a selected dependency only when a requested core responsibility actually uses it. Discover supplied local UI packages and integrate all applicable core responsibilities through the contract reference. Packages supplied for these responsibilities are applicable dependencies; optional unrelated toolkits and a recommended local database are not required merely because the reference app used them. Keep both database skills separate. Missing project configuration such as the backend URL is reported explicitly; never invent a working endpoint or claim a live API was tested.

Use normal transport certificate validation. Do not copy token logging, universal certificate acceptance, a transport singleton that ignores injected configuration, or no-op setters. Preserve the ApiConsumer/Failure boundaries while implementing real request forwarding and error translation. Auth integration, if already present, preserves its actual token/session contract without logging credentials.

Respect project rules for comments. When comments are prohibited, put token purpose/provenance in the theme README instead of adding code comments. The explicitly requested main command documentation block is the sole startup exception for full/new startup work: copy [the canonical block](references/main-command-block.dart.txt) verbatim to the bottom of `lib/main.dart`, after `main()`, never above the imports and never with a `library;` directive; the documented commands neither authorize execution nor dependency installation. A scoped helper does not require inserting documentation into unrelated main code. Preserve generated/vendor comments.

## Wire and verify

Complete the [iOS and Android setup](references/core-contracts.md#ios-and-android-setup) for every package integrated or affected by the selected core work, including required native configuration and permissions. This invocation authorizes those necessary platform edits and targeted local builds/runtime checks, subject to project restrictions. Scoped Dart/UI-only repairs do not trigger unrelated native rebuilds. Never claim native behavior from mocked tests.

For full/new app-root wiring, use `MyApp` in `lib/my_app.dart`, preserving working behavior. Initialize directly in `lib/main.dart`; do not introduce `app_bootstrap.dart`, a production startup helper or an alternative root name. Initialize localization and both cache helpers concurrently in one awaited `Future.wait` as documented, call `registerAppDependencies()` to register core then features, load the SkinRegistry with error reporting, install the selected state observer, and only then construct root skin state. On the default get_it stack, import `core/di/injection.dart` wherever container access is needed and use the canonical global `sl` directly. Use `const MyApp({super.key})` with no locator field/parameter and construct `const MyApp()` from main; root providers resolve explicit `sl<T>()` services. On the Bloc stack, include the factory-owned NetworkCubit with eager normal provider creation and disposal, as specified in [root network ownership](references/core-contracts.md#root-network-ownership). MyApp reads the public `AppRouter.initialRoute` getter; the router owns the entry decision. Preserve actual service constructor dependencies; selected alternative DI keeps its verified mechanics. Configure the root with the selected localization/state/typography mechanisms, AppTheme.of(skin), router and keys. Preserve the existing entry screen and navigation policy.

For scoped completion, extend existing startup/DI only where required by the selected contracts. Preserve unrelated root constructors/providers and do not add network, skins or localization just because full-bootstrap recipes list them. Complete each newly needed registration/readiness boundary exactly once before returning to the caller.

Run required code generation through the selected generator, format changed authored files and update the existing DI registration test when registrations changed. Exercise affected contracts through [core/capture preflight](../visual-verification/references/preflight.md); full/new foundations cover service resolution, theme/skin selection, localization, text/fields/buttons/sheets and relevant failures. Scoped completion checks its changed contracts and affected consumers without a whole-core showcase. If tests were requested, use `flutter-testing` for focused boundary tests; do not create a generic suite as scaffolding ceremony.

Return to the calling implementation after verifying the selected core work; let its final `flutter-review` gate cover the batch rather than running it twice. Standalone core work finishes with that gate, including applicable manual contract/startup inspection. Report the selected scope, created/completed/preserved components, mechanics, dependencies added, missing decisions, executed checks and unrelated gaps separately. A successful inspector/compilation or a completed partial contract is not a whole-core claim.
