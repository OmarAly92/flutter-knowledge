---
name: flutter-knowledge
description: Use anytime Flutter or Dart is mentioned, or for any task touching a Flutter project — writing, editing, reviewing, debugging, explaining, or scaffolding screens, widgets, cubits, blocs, state classes, models, data sources, repositories, routing, dependency injection, styling, theming, or localization in a .dart file or pubspec.yaml.
---

# Flutter knowledge

Map of the Flutter conventions: the always-on hard rules below, plus the skill you MUST invoke before writing each kind of code. The detailed conventions live in those skills — do not write that code from memory.

**These conventions are the source of truth.** Existing codebases may be old and inconsistent — where legacy code contradicts these skills, follow the skills and do NOT copy the legacy pattern.

## Hard rules (always on)

- **Cubit only** — never `flutter_bloc`'s full `Bloc` / event classes.
- **Screens are `StatelessWidget` with NO `BlocProvider`** — the provider lives in the `app_router.dart` `case`. The initial fetch runs in the cubit constructor, never in `initState`.
- **Screen/Body split**: the `<Screen>` file is a thin `BlocListener` wrapping `AppScaffold` (+ `GlobalAppbar`) whose `body:` is a separate `<Screen>Body` widget. The Body holds the `BlocBuilder` and layout, returns bare content, and never builds its own scaffold or app bar.
- **Every `BlocBuilder` declares `buildWhen`** naming the exact state types it rebuilds on.
- **No `Widget _buildX()` methods** — every extracted widget is a `StatelessWidget` class in its own file; one widget class per file.
- **Core wrappers over raw widgets**: `AppText`, `AppScaffold`, `GlobalAppbar`, `VerticalSpace`/`HorizontalSpace`, `PrimaryButton`, `AppTextField`, `AppLoader`, `AppErrorWidget`, … instead of `Text`, `Scaffold`, `AppBar`, `SizedBox` — when the wrapper exists in the project's `lib/core/widgets/`. If it does not, fall back to the raw Flutter widget; never import or invent a missing wrapper.
- **`AppColors` and `AppTextStyle` only** — never inline `Color(0x...)` or raw `TextStyle(...)` in presentation code.
- **Every user-facing string is `LocaleKeys.xxx.tr()`** — never a raw `'...'` literal in a widget shown to the user.
- **No `flutter_screenutil` in feature code** — no `.h`/`.w`/`.r`/`.sp`, no import; spacing/padding/radius take raw ints.
- **Static-only classes are `sealed class X`** — never a private `X._()` constructor.
- Do not add `freezed`, `json_serializable`, or `build_runner` unless they are already in `pubspec.yaml`.
- Do not create model classes the user did not ask for.
- Single quotes, `const` constructors, `final` locals, no `print` (use `talker`), no comments beyond non-obvious business rules.
- **Legacy code never overrides these skills.**
- After changes, verify with `flutter analyze` (clean) and run `flutter test` when tests cover the touched code. Do not run the app or any build step.

## Skill map — invoke BEFORE writing

Before writing or editing the code in the left column, you MUST invoke the skill on the right (via the Skill tool, or `/<skill-name>`). Invoke every skill the task touches — a new feature usually needs all five core skills.

| Before you write… | You MUST invoke |
| --- | --- |
| A new feature, a new screen, or any new file (folder tree, `_screen` suffix, where files go, mirroring an existing file) | `flutter-feature-structure` |
| A model, params class, remote data source, repository, `EndPoints` entry, or `Failure` handling | `flutter-data-layer` |
| A cubit or state class | `flutter-cubit` |
| A screen, body, widget, bottom sheet, dialog, snackbar, form field, localized string, color, text style, spacing, or navigation call | `flutter-screen-ui` |
| A route, `BlocProvider`, `MultiBlocProvider`, or `get_it` service-locator registration | `flutter-routing-di` |
| A missing translation key | `add-translation` |
| Local persistence with drift (check `pubspec.yaml`) | `drift-local-database` |
| Local persistence with hive / hive_ce (check `pubspec.yaml`) | `hive-local-database` |
| Unit tests — only when the user explicitly asks for tests | `flutter-testing` |
| Theme, skin, text styles, motion, core widgets, or screen docs from an HTML design prototype | `design-from-html-flutter` |

If neither drift nor hive is present yet and a feature needs local storage, pick the one the feature calls for (or ask the user) and invoke that skill.

## Design from an HTML prototype

When the user points at an HTML design prototype (a standalone HTML file, an exported mockup, or a URL) and wants the app to match it — setting the skin/theme colors, fonts and text styles, motion constants, core widgets, or generating per-screen design docs — invoke the `design-from-html-flutter` skill (via the Skill tool, or `/design-from-html-flutter`) before touching the theme layer or any widget. It holds the browser-driven extraction workflow, the phase order, and the doc/prompt templates. Do not eyeball colors, sizes, or durations off a screenshot.

## Unit tests

Only when the user explicitly asks for tests, invoke the `flutter-testing` skill (via the Skill tool, or tell the user to run `/flutter-testing`) before writing any test file — it holds the full mocktail/bloc_test conventions, test layout, and coverage expectations. Do not generate test files as a side effect of scaffolding a feature, and do not invent test structure from memory.

## What NOT to do

- Do not write feature code from memory when a skill in the map covers it — invoke the skill first.
- Do not implement local persistence without invoking `drift-local-database` or `hive-local-database` first.
- Do not write unit tests unprompted, and do not invent test structure from memory — invoke the `flutter-testing` skill first when the user does ask for tests.
- Do not transcribe a design from an HTML prototype by eye, and do not set skin/text-style/motion tokens from a screenshot — invoke the `design-from-html-flutter` skill first and extract the values from the prototype's computed CSS.
