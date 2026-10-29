---
name: flutter-feature-structure
description: Use before creating Flutter features, screens or files, or deciding folder placement and naming under lib/feature/ and lib/core/.
---

# Flutter feature structure

For implementation, read the [project configuration contract](../flutter-init/references/configuration.md) before applying package-specific instructions. Keep its conventions and naming; adapt package-specific examples through the selected mechanics.

Invoked by the `flutter-knowledge` skill (or directly via `/flutter-feature-structure`) before creating a feature, a screen, or any new file in one. Related skills: `flutter-data-layer` for `data/`, `flutter-state-management` for `logic/`, `flutter-screen-ui` for `ui/`, `flutter-routing-di` for wiring, and `drift-local-database` / `hive-local-database` for local persistence.

**These conventions are the source of truth.** Existing codebases may be old and inconsistent — where legacy code contradicts this skill, follow the skill and do NOT copy the legacy pattern.

## Feature architecture

The file tree and naming stay fixed. Package API names in examples (GetIt, Cubit base classes, Equatable) follow the configuration contract; do not replace the selected package to imitate an example.

Features live under `lib/feature/<feature>/` (snake_case — singular `feature`, NOT `features`). Every feature follows this tree — the presentation screen directory MUST be suffixed `_screen`:

```
<feature>_injection.dart                  # register<Feature>Dependencies() — see flutter-routing-di
data/
  data_source/<feature>_remote_data_source.dart
  data_source/<feature>_local_data_source.dart   # only for local-only / hybrid features
  data_source/<feature>_device_data_source.dart  # only for plugin calls: permissions, camera, package info
  model/                                  # every XModel, including the ones a screen displays
  model/params/                           # every XParams: request params and screen/route inputs
  repository/<feature>_repository.dart
presentation/
  widget/                                 # only widgets used by 2+ screens of this feature
  <screen>_screen/                        # NOTE the _screen suffix
    logic/
      <screen>_cubit.dart
      <screen>_state.dart
      helpers/                            # builders, mappers, formatters, constants for this screen
    ui/
      <screen>_screen.dart
      widgets/
```

Omit `data/` entirely for UI-only features with no models or params. A local-only or hybrid feature also needs local persistence — invoke the matching local-database skill for that before writing any local data source or storage code: `drift-local-database` if the project uses drift, `hive-local-database` if it uses Hive.

### Where each file goes

- **Widgets** — place by who uses them. Used by one screen → that screen's `ui/widgets/`. Used by two or more screens of the same feature → `presentation/widget/` (singular), next to the `_screen` dirs. Used by screens of different features → `lib/core/widgets/<role>/`. When a second screen starts using a widget, move it up a level rather than importing it from another screen's `ui/widgets/`. `presentation/` holds only `<screen>_screen/` dirs and `widget/` — no `widgets/`, `components/`, `shared/` or loose files.
- **`logic/` holds only `<screen>_cubit.dart`, `<screen>_state.dart` and `helpers/`.** Nothing else sits loose in `logic/`.
- **A class with fields is a model or params, never a logic file.** A class that carries data for the screen to show (a board, summary, row, slot, item, view data) is an `XModel` in `data/model/`. A class that carries input into a cubit, route or builder (inputs, args, filters) is an `XParams` in `data/model/params/`. Follow `flutter-data-layer` for both.
- **`logic/helpers/` holds behavior without data**: builders/mappers that turn models into a display model, formatters, the screen's option constants and its enums (such as `AppNavTab`) — `sealed class` with static members only, or an `enum` (`CrewSettingsBoardBuilder.build(...)`, `CrewSettingsNames.join(...)`, `CrewSettingsOptions.pushUpsMax`). A helper used by screens of other features goes in `lib/core/helpers/` instead.

The main screen widget lives in `ui/`; every section/child widget lives in its own file under `ui/widgets/` or one of the shared widget dirs above and gets imported (see `flutter-screen-ui`).

## Core layout

`lib/core/` holds what features share, in these top-level folders:

| Folder | Holds |
| --- | --- |
| `theme/` | design tokens (`AppTokens`, `context.tokens`), skins, typography, motion, `AppTheme` — see `flutter-app-theme` |
| `l10n/` | `AppLocales`, the generated `locale_keys.g.dart`, locale extensions, text-direction helpers |
| `layout/` | breakpoints and screen-size extensions (`context.width`, `context.windowSize`, …) |
| `router/` | `app_router.dart` + its `routes_strings.dart` part — see `flutter-routing-di` |
| `data/` | `api/` (`ApiConsumer`, `EndPoints`, `GlobalResponse`), `cache/`, `database/`, `error_handling/` (`Failure`, `Result`) |
| `di/` | `injection.dart` — the global `sl` and `registerCoreDependencies` |
| `helpers/` | small tools (`AppAssets`, validators, logger) plus `extensions/` |
| `services/` | shared services (NetworkStatus, session, …) and their composition-owned state (`network/logic/NetworkCubit` follows the core ownership contract) |
| `widgets/` | core widgets grouped by role (`buttons/`, `inputs/`, `text/`, `layout/`, `sheets/`, `feedback/`, …) — put a new one in the folder for what it does, never at the root |

**A subfolder exists only once it holds two or more files** — a lone helper or service sits loose in its parent (`helpers/app_assets.dart`, not `helpers/assets/app_assets.dart`). `test/core/` mirrors the same layout. A new shared file goes in the folder for what it is; do not recreate `config/`, `utils/` or `app_themes/`.

## Mirror an existing equivalent file

Before writing each file, read the equivalent file from an existing feature in the current codebase and mirror its style and import order. Do not invent a different shape:
- Cubit: pick an existing `*_cubit.dart` — note it kicks off the initial fetch from inside the constructor body, NOT from the screen's lifecycle.
- State: pick an existing `*_state.dart` — sealed class, `final class` variants, Equatable with `props`.
- Remote data source: an existing `*_remote_data_source.dart` (abstract + `*Imp` using `ApiConsumer`).
- Repository: an existing repository (abstract + `*Imp` returning `FutureResult<T>` — the typedef wrapping the failure/success result — gated on `NetworkStatus`).

Where the existing file contradicts the conventions in `flutter-data-layer`, `flutter-state-management`, `flutter-screen-ui`, or `flutter-routing-di`, those skills win — mirror style and import order, not legacy patterns.

## What NOT to do

- Do not name the features directory `features` — it is `lib/feature/`.
- Do not drop the `_screen` suffix from the presentation screen directory.
- Do not create `presentation/widgets/` or any other dir in `presentation/` besides `<screen>_screen/` and `widget/`; do not import one screen's `ui/widgets/` file from another screen.
- Do not declare a class with fields in `logic/` or `logic/helpers/` (`XBoard`, `XInputs`, `XArgs`, `XSlot`) — it is an `XModel` in `data/model/` or an `XParams` in `data/model/params/`.
- Do not put builders, formatters or constants loose in `logic/` — they go in `logic/helpers/`.
- Do not invent a file shape without first reading the equivalent file from an existing feature.
- Do not create model classes the user did not ask for.
