---
name: flutter-core
description: Create or complete a Flutter project's shared core using the Flutter Knowledge conventions. Use only when the user explicitly invokes /flutter-core or asks to bootstrap or complete the core, usually after /flutter-init. Do not bootstrap core as a side effect of ordinary screen work.
---

# Create or complete Flutter core

`/flutter-core [project-path]`

Resolve an optional project path from the invocation; otherwise use the current Flutter project. Verify its `pubspec.yaml`. The user authorizes creating/completing the essential core, necessary dependency/asset declarations, localization generation and app-root wiring. Preserve existing behavior and package choices. No business features, authentication policy, backend URLs, database schema or unrelated toolkit installation are implied. Required core API and supplied-local-package contracts live in [core contracts](references/core-contracts.md#core-api-alignment).

## Initialize first

Read [the configuration contract](../flutter-init/references/configuration.md). If `flutter-knowledge.yaml` is absent, invoke `flutter-init` and run its initializer before package-dependent core work. Calling this skill before `/flutter-init` is supported. Check an existing config; when catalog categories are missing, rerun the initializer to fill them while preserving explicit choices. Unresolved choices block only their dependent components. Defaults live exclusively in the initializer's catalog.

## Inspect and plan the completion

Run the read-only helper:

```bash
python3 "<skill-directory>/scripts/inspect_core.py" --project "<flutter-project>" --json
```

It reports contract evidence, missing conventional files, configured paths and package adaptations. It does not generate code or certify completeness. Inspect actual implementations and callers, not just filenames or class presence. Use config discovery to find existing equivalents; do not create a parallel API/theme/router when a custom contract already fulfills the role. The helper's [contract inventory](references/core-contracts.json) is a transient inspection aid, not a saved component inventory in project configuration.

Make a short missing/incomplete/preserved table, then implement the authorized gaps. Reuse working equivalents and preserve custom routes, registrations, constructors, theme values, assets/fonts, locales, cache keys and startup effects. A rerun should add no duplicate registrations, providers, translations or declarations. Follow the existing theme architecture decision in `flutter-app-theme`; core setup is not permission for an unrequested migration.

## Build the essentials

Read [core contracts and startup](references/core-contracts.md). Apply the owning skills before implementation:

- `flutter-feature-structure`: core locations and existing equivalents.
- `flutter-routing-di`: router library/parts, typed core registrations and app dependency entry.
- `flutter-data-layer`: consumer, endpoints, GlobalResponse, Result/Failure and error boundaries.
- `flutter-state-management`: root state owners, fields, equality and disposal.
- `flutter-app-theme`: all seven token groups, skins, registry, selection and ThemeData mapping.
- `flutter-screen-ui`, `flutter-accessibility-rtl`, `flutter-responsive-layout`: shared wrappers, direction extensions, semantics and constraints.
- `add-translation`: required English/Arabic keys and generated accessors for the selected localization backend.

Create the entire requested foundation: routing/DI; theme/tokens/skins/loading; API/error handling; network; layout; localization/preferences/logger; principal text/scaffold/appbar/container/spaces/button/field/sheet/feedback wrappers; app-root wiring. Complete registrations as well as declarations. An API class left unregistered or an AppTokens extension absent from ThemeData is an incomplete core.

Include both ordinary and secure cache foundations through [cache storage](references/core-contracts.md#cache-storage): sensitive values use `SecureCacheHelper`/`SecureCacheKeys`; ordinary preferences stay in `CacheHelper`/`CacheKeys`. Apply the selected secure-storage backend and initialize it before any token-dependent consumer or router decision. This does not authorize inventing authentication features.

The default recipes follow the reference architecture, not its application features. Use target package imports from pubspec's `name`. Selected alternative packages keep the same responsibilities, naming and lifetimes through their verified APIs. Read only applicable package-adaptation sections. Never switch an alternative to a default just to match a recipe.

Add a selected dependency only when a requested core responsibility actually uses it. Discover supplied local UI packages and integrate all applicable core responsibilities through the contract reference. Packages supplied for these responsibilities are applicable dependencies; optional unrelated toolkits and a recommended local database are not required merely because the reference app used them. Keep both database skills separate. Missing project configuration such as the backend URL is reported explicitly; never invent a working endpoint or claim a live API was tested.

Use normal transport certificate validation. Do not copy token logging, universal certificate acceptance, a transport singleton that ignores injected configuration, or no-op setters. Preserve the ApiConsumer/Failure boundaries while implementing real request forwarding and error translation. Auth integration, if already present, preserves its actual token/session contract without logging credentials.

Respect project rules for comments. When comments are prohibited, put token purpose/provenance in the theme README instead of adding code comments. The explicitly requested main command documentation block is the sole startup exception: copy [the canonical block](references/main-command-block.dart.txt) verbatim into `lib/main.dart`; the documented commands neither authorize execution nor dependency installation. Preserve generated/vendor comments.

## Wire and verify

Complete the [iOS and Android setup](references/core-contracts.md#ios-and-android-setup) for every integrated core package, including required native configuration and permissions. This core invocation authorizes necessary platform edits and targeted local builds/runtime checks, subject to project restrictions. Do not stop at Dart-only checks or claim both platforms work from mocked tests.

Use `MyApp` in `lib/my_app.dart`, preserving its working behavior. Initialize directly in `lib/main.dart`; do not introduce `app_bootstrap.dart`, a production startup helper or an alternative root name. Initialize localization and both cache helpers in the documented order, call `registerAppDependencies()` to register core then features, load the SkinRegistry with error reporting, install the selected state observer, and only then construct root skin state. On the default get_it stack, import `core/di/injection.dart` wherever container access is needed and use the canonical global `sl` directly. Use `const MyApp({super.key})` with no locator field/parameter and construct `const MyApp()` from main; root providers resolve explicit `sl<T>()` services. On the Bloc stack, include the factory-owned NetworkCubit with eager normal provider creation and disposal, as specified in [root network ownership](references/core-contracts.md#root-network-ownership). MyApp reads the public `AppRouter.initialRoute` getter; the router owns the actual entry decision. Preserve actual service constructor dependencies; selected alternative DI keeps its verified mechanics. Configure the app root with the selected localization/state/typography mechanisms, AppTheme.of(skin), router and keys. Preserve the existing entry screen and navigation policy.

Run code generation through the actual selected generator, format changed authored files and update the existing DI registration test. Exercise the new core through [core/capture preflight](../visual-verification/references/preflight.md): actual service resolution, theme/skin selection, localization, text/fields/buttons/sheets and relevant failure behavior. If tests were requested, add focused tests for these boundaries using `flutter-testing`; do not create a generic test suite as scaffolding ceremony.

Finish with `flutter-review`, including manual contract/startup inspection. Report created/completed/preserved components, selected mechanics, dependencies actually added, missing project decisions, executed checks and remaining gaps. A successful inspector or compilation alone is not a complete core claim.
