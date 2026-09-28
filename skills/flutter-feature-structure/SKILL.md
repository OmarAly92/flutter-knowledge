---
name: flutter-feature-structure
description: Feature folder layout for a Flutter project — lib/feature/<feature>/ tree, data/ vs presentation/, the `_screen` directory suffix, logic/ui/widgets placement, and the "read an existing equivalent file first and mirror it" rule. Use before creating a new Flutter feature, screen, or file, or when deciding where a Dart file belongs.
---

# Flutter feature structure

Invoked by the `flutter-knowledge` skill (or directly via `/flutter-feature-structure`) before creating a feature, a screen, or any new file in one. Related skills: `flutter-data-layer` for `data/`, `flutter-cubit` for `logic/`, `flutter-screen-ui` for `ui/`, `flutter-routing-di` for wiring, and `drift-local-database` / `hive-local-database` for local persistence.

**These conventions are the source of truth.** Existing codebases may be old and inconsistent — where legacy code contradicts this skill, follow the skill and do NOT copy the legacy pattern.

## Feature architecture

Features live under `lib/feature/<feature>/` (snake_case — singular `feature`, NOT `features`). Every feature follows this tree — the presentation screen directory MUST be suffixed `_screen`:

```
data/
  data_source/<feature>_remote_data_source.dart
  data_source/<feature>_local_data_source.dart   # only for local-only / hybrid features
  model/                                  # add models as needed
  model/params/                           # request params classes
  repository/<feature>_repository.dart
presentation/
  <screen>_screen/                        # NOTE the _screen suffix
    logic/
      <screen>_cubit.dart
      <screen>_state.dart
    ui/
      <screen>_screen.dart
      widgets/
```

Omit `data/` entirely for UI-only features. A local-only or hybrid feature also needs local persistence — invoke the matching local-database skill for that before writing any local data source or storage code: `drift-local-database` if the project uses drift, `hive-local-database` if it uses Hive.

The main screen widget lives in `ui/`; every section/child widget lives in its own file under the sibling `ui/widgets/` dir and gets imported (see `flutter-screen-ui`).

## Mirror an existing equivalent file

Before writing each file, read the equivalent file from an existing feature in the current codebase and mirror its style and import order. Do not invent a different shape:
- Cubit: pick an existing `*_cubit.dart` — note it kicks off the initial fetch from inside the constructor body, NOT from the screen's lifecycle.
- State: pick an existing `*_state.dart` — sealed class, `final class` variants, Equatable with `props`.
- Remote data source: an existing `*_remote_data_source.dart` (abstract + `*Imp` using `ApiConsumer`).
- Repository: an existing repository (abstract + `*Imp` returning `FutureResult<T>` — the typedef wrapping the failure/success result — gated on `NetworkStatus`).

Where the existing file contradicts the conventions in `flutter-data-layer`, `flutter-cubit`, `flutter-screen-ui`, or `flutter-routing-di`, those skills win — mirror style and import order, not legacy patterns.

## What NOT to do

- Do not name the features directory `features` — it is `lib/feature/`.
- Do not drop the `_screen` suffix from the presentation screen directory.
- Do not invent a file shape without first reading the equivalent file from an existing feature.
- Do not create model classes the user did not ask for.
