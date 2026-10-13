---
name: flutter-knowledge
description: Use anytime Flutter or Dart is mentioned, or for any task touching a Flutter project — writing, editing, reviewing, debugging, explaining, or scaffolding screens, widgets, cubits, blocs, state classes, models, data sources, repositories, routing, dependency injection, styling, theming, or localization in a .dart file or pubspec.yaml.
---

# Flutter knowledge

For implementation, read the [project configuration contract](../flutter-init/references/configuration.md) before applying package-specific instructions. Keep its conventions and naming; adapt package-specific examples through the selected mechanics.

Map of the Flutter conventions: the always-on hard rules below, plus the skill you MUST invoke before writing each kind of code. The detailed conventions live in those skills — do not write that code from memory.

**These conventions are the source of truth.** Existing codebases may be old and inconsistent — where legacy code contradicts these skills, follow the skills and do NOT copy the legacy pattern.

## Task entry

Select the applicable route in [task workflows](references/workflows.md) before acting: planning, implementation, initialization, tests and findings-only review have different completion requirements. That reference owns configuration handoffs and the final report. Directly invoked specialists use the same route without restarting the map.

## Hard rules (always on)

- **Configured state backend, fixed conventions** — invoke `flutter-state-management`. For `flutter_bloc` / `bloc`, use Cubit, never event-based Bloc. Alternative packages retain the same owner-held data, operation-specific state names and lifecycle responsibilities.
- **Screens are `StatelessWidget` with NO state-owner/provider construction** — the provider lives at the route/composition boundary (the `lib/core/router/app_router.dart` case on the default stack). The initial fetch runs on state-owner creation (the Cubit constructor by default), never in screen `initState`. Configured routers keep provider ownership at their route/composition boundary. Bloc root NetworkCubit is factory-created by its normal eager provider and closed by that provider; see `flutter-core`. AppRouter owns its public initial-route decision; MyApp only reads it.
- **Screen/Body split**: the `<Screen>` file handles effects and wraps `AppScaffold` (+ `GlobalAppbar`) whose `body:` is a separate `<Screen>Body` widget. The Body holds selective state rebuilding and layout (`BlocListener` / `BlocBuilder` on the default stack), returns bare content, and never builds its own scaffold or app bar.
- **Every state-driven builder filters the exact operation states it rebuilds on** — `BlocBuilder.buildWhen` on the default stack, the selected backend's equivalent otherwise.
- **No `Widget _buildX()` methods** — every extracted widget is a `StatelessWidget` class in its own file; one widget class per file except the ordinary/sliver spacing family in `core/widgets/layout/space_widgets.dart` (owned by `flutter-screen-ui`).
- **Core wrappers over raw widgets**: `AppText`, `AppScaffold`, `GlobalAppbar`, `VerticalSpace`/`HorizontalSpace`, `PrimaryButton`, `AppTextField`, `AppLoader`, `AppErrorWidget`, … instead of `Text`, `Scaffold`, `AppBar`, `SizedBox` — when the wrapper exists in the project's `lib/core/widgets/`. If it does not, fall back to the raw Flutter widget; never import or invent a missing wrapper.
- **Every design value is a token read through `context.tokens`** — `tokens.skin` (colors), `tokens.space` (gaps, padding), `tokens.radius` (corners), `tokens.text` (text styles), `tokens.elevation` (shadows), `tokens.motion` (durations, curves, springs), `tokens.shape`. Never inline `Color(0x...)`, raw `TextStyle(...)`, a literal radius, or an animation `Duration`/`Curves` in presentation code. Read tokens in `build`; in `initState`, `dispose`, a `late final` initializer or a cubit (where `Theme.of` asserts) use `AppMotion.standard` / `AppShapes.standard` instead.
- **Every user-facing string uses the configured localization accessor** (`LocaleKeys.xxx.tr()` for easy_localization) — never a raw `'...'` literal in a widget shown to the user.
- **No `flutter_screenutil` in feature code** — no `.h`/`.w`/`.r`/`.sp`, no import; spacing and radii come from `context.tokens.space` / `context.tokens.radius`.
- **Static-only classes are `sealed class X`** — never a private `X._()` constructor.
- Do not add `freezed`, `json_serializable`, or `build_runner` unless they are already in `pubspec.yaml`.
- Do not create model classes the user did not ask for.
- Single quotes, `const` constructors, `final` locals, no `print` (use the configured logger; `talker` by default), no comments beyond non-obvious business rules — with the explicitly requested main command-block exception owned by `flutter-core`; except the `///` doc comment every theme token, skin slot and text style carries (`flutter-app-theme`).
- **Legacy code never overrides these skills.**
- After implementation, invoke `flutter-review` for the read-only gate and manual architectural checks. During implementation, format changed files (`dart format <file> …`, never a whole folder) and run focused checks. The final review gate owns required whole-project analysis/tests once the batch settles; follow more frequent project requirements and rerun affected checks after further changes. Do not duplicate a broad suite immediately before that gate. Do not run the app or any build step unless the project's `CLAUDE.md` / `AGENTS.md` allows it.

## Skill map — invoke BEFORE writing

Before writing or editing the code in the left column, you MUST invoke the skill on the right (via the Skill tool, or `/<skill-name>`). Invoke every skill the task touches — a new feature usually needs all five core skills.

| Before you write… | You MUST invoke |
| --- | --- |
| Initialize package selections from `pubspec.yaml`, or create/refresh `flutter-knowledge.yaml` | `flutter-init` |
| Create or complete the shared core — only when the user explicitly invokes `/flutter-core` or asks to bootstrap core; never as a side effect of screen work | `flutter-core` (manual; it runs `flutter-init` first when config is absent) |
| A new feature, a new screen, or any new file (folder tree, `_screen` suffix, where files go, mirroring an existing file) | `flutter-feature-structure` |
| A model, params class, remote data source, repository, `EndPoints` entry, or `Failure` handling | `flutter-data-layer` |
| A state owner, cubit, controller or state class | `flutter-state-management` |
| A screen, body, widget, bottom sheet, dialog, snackbar, form field, localized string, color, text style, spacing, or navigation call | `flutter-screen-ui` |
| A route, `BlocProvider`, `MultiBlocProvider`, or `get_it` registration (`<feature>_injection.dart`, `lib/core/di/`) | `flutter-routing-di` |
| A missing translation key | `add-translation` |
| Local persistence with configured drift | `drift-local-database` |
| Local persistence with configured hive / hive_ce | `hive-local-database` |
| User-facing controls, semantics, RTL/directional behavior or text scaling | `flutter-accessibility-rtl` |
| Constraints, breakpoints, overflow, keyboard insets or multiple layout targets | `flutter-responsive-layout` |
| Large lists/grids, image decoding, animation cost, build work or measured jank | `flutter-performance` |
| A findings-only review, readiness check or substantial work before handoff/commit/PR | `flutter-review` |
| Design-driven screen capture, source comparison and completion evidence | `visual-verification` + `golden-tests` |
| Unit tests — only when the user explicitly asks for tests | `flutter-testing` |
| An animation (duration, curve, spring, stagger, page transition); a design's values matched to tokens, and whether one becomes a token; a new color, spacing, radius, text style, shadow, motion or shape token; a skin, the skin picker, or `ThemeData`; an audit for hardcoded values; or any file under `lib/core/theme/` | `flutter-app-theme` |
| A screen, or a component inside one, built to match an HTML prototype or a Figma frame | `html-to-widget` / `figma-to-widget` for the supplied source |
| Apply the whole HTML design to an existing core theme and import its original assets/fonts, after `/flutter-core` | `set-theme-from-html` + `flutter-app-theme`; later screen work uses `html-to-widget` |
| Whole-app design planning or source extraction for foundations | `html-to-widget` / `figma-to-widget`; follow the planning/foundations route in task workflows |

Older project: if it has no `lib/core/theme/app_tokens.dart` (and `grep -rn "class AppTokens" lib` finds nothing), it predates `context.tokens`. Keep using its own theme classes (`context.skin` or `AppColors`, `AppTextStyle`, static `AppMotion`) and invoke `flutter-app-theme`, which says how; do not migrate it unless the user asks.

Resolve storage through `flutter-init` and the project config. Recommendations do not install storage; use only what the feature needs. Ambiguous engines require a choice. Keep the two database skills separate.

## Unit tests

For explicitly requested unit tests, invoke `flutter-testing` before writing the test files; it owns the test layout, coverage and configured tooling. Updating the existing DI registration test is part of wiring dependencies; the design workflow must create or reuse its required golden capture harness and perform source comparison under the design completion contract. Otherwise do not generate test files as a side effect of scaffolding a feature, and do not invent test structure from memory.

## What NOT to do

- Do not write feature code from memory when a skill in the map covers it — invoke the skill first.
- For configured Drift or Hive, invoke its matching database skill before local persistence. For another selected engine, apply the configuration contract's persistence guidance without importing either engine's types.
- Do not generate feature unit-test suites unprompted. Keep the DI registration and design-golden exceptions above scoped to their workflows; use `flutter-testing` for requested unit tests.
- Do not transcribe a design from an HTML prototype by eye, and do not set skin/text-style/motion tokens from a screenshot — read the values from the prototype's computed CSS, through the shared HTML source extraction used by `html-to-widget` / `set-theme-from-html`; use `flutter-app-theme` for token decisions.
