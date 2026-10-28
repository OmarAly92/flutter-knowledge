---
name: flutter-state-management
description: Use before writing Flutter state owners, Cubits, controllers, state classes, state naming or lifecycle behavior, using the configured state-management package.
---

# Flutter state management

For implementation, read the [project configuration contract](../flutter-init/references/configuration.md) before applying package-specific instructions. Keep its conventions and naming; adapt package-specific examples through the selected mechanics.

Invoked by the `flutter-knowledge` skill (or directly via `/flutter-state-management`) before writing or editing any `*_cubit.dart` or `*_state.dart`. Related skills: `flutter-data-layer` for the repository the cubit calls, `flutter-routing-di` for registering the cubit and passing constructor parameters, `flutter-screen-ui` for how the UI consumes it, and `flutter-testing` when the user asks for cubit tests.

**These conventions are the source of truth.** Existing codebases may be old and inconsistent — where legacy code contradicts this skill, follow the skill and do NOT copy the legacy pattern.

## State ownership and naming

The skill name changed; Dart names did not. Keep `XCubit`, `XState`, `_cubit.dart`, `_state.dart`, and the operation-specific names below even when another configured package implements the owner. For Bloc packages, use [the Cubit reference](references/cubit.md). For another backend, apply [the state adaptation contract](../flutter-init/references/package-adaptation.md#state-management) and verify its actual APIs.

- With `flutter_bloc` / `bloc`, use `Cubit` — never event-based `Bloc`. A configured alternative must preserve the same state-owner contract.
- State classes: sealed base class, `final class` variants, field-based equality through the configured mechanism (Equatable with `props` on the default stack). The state file is a `part` of the cubit file: `part 'x_state.dart';` in the cubit, `part of 'x_cubit.dart';` in the state.
- **State naming**: every variant must end with the `State` suffix, and states are **per cubit method**: one shared `XInitialState`, then `<Method>LoadingState`, `<Method>SuccessState`, `<Method>FailureState` for each method (e.g. `GetOrdersLoadingState`). Failure states carry the `Failure` payload. The legacy `XInitial` form (no suffix) exists in old files — do NOT copy it.
- **Cubit owns its data lifecycle**: if the cubit has a fetch that should run when the screen opens, call it from the cubit's constructor body on the default stack, or the selected backend's owner-creation hook — never from a `StatefulWidget.initState`.
- **`logic/` holds only the cubit, its state and `helpers/`**: builders, mappers, formatters and option constants go in `logic/helpers/` as `sealed class`es with static members; any class with fields the cubit builds or receives is an `XModel` / `XParams` under `data/model/` (see `flutter-feature-structure`).
- **Cubit stores the data, not the state**: keep the response model in a plain nullable field directly on the cubit (`XModel? xModel;`) so the UI can read it after the success emit — success states stay payload-free. The one exception is the nav bar's `ChangeTabSuccessState(tab)` in the [app nav bar recipe](../flutter-routing-di/references/app-nav-bar.md). Don't wrap it in a private field plus a public getter (`_xModel` + `get xModel`) — that's boilerplate for no benefit here; a direct field is simpler.
- **All widget state lives on the cubit**: `TextEditingController`s, `ScrollController`s, form keys, dropdown/picker selections — declared as direct field initializers (`final nameController = TextEditingController();`), not assigned inside the constructor body. When the cubit receives existing data to edit (e.g. an initial model passed in via `registerFactoryParam`), pre-fill each controller with that value directly — `TextEditingController(text: initialModel.name)` — assigned through the constructor's initializer list; never construct it empty and set `.text` afterwards. Dispose disposables in cubit `close()` on the default stack, or in the selected backend's owner-disposal hook.

The Cubit reference also shows initializer-list prefill for an edit screen.

For root startup, follow [the core startup contract](../flutter-core/references/core-contracts.md#startup-order): install the selected observer in direct `main.dart` initialization before root owners are created. Bloc/Talker uses the registered shared logger and metadata-only debug observation; other state selections do not import/install Bloc.

For the Bloc root NetworkCubit, follow [root network ownership](../flutter-core/references/core-contracts.md#root-network-ownership): factory registration, eager provider-owned creation/close, payload-free connectivity states and guarded initial-check/stream/restoration lifecycle. Its online flag and `isOnline` getter describe connectivity; they are not fetched model payloads. Other selected backends retain equivalent verified ownership.

## Async lifecycle and overlap

After an awaited operation and before changing owner fields, controllers or public state, verify the owner is still alive. Use the backend's verified lifecycle mechanism (`isClosed` for Cubit) and cancel subscriptions/requests where the existing API supports it. Do not keep a BuildContext in the owner.

Choose overlap behavior per operation. Fetch/search may discard superseded results; writes need their own ordering or duplicate-submission policy. A disposal guard alone does not prevent a stale earlier request from overwriting a newer result. Keep these protections inside the same owner, without changing model/state naming or payload placement.

Read [Riverpod](references/riverpod.md) for that family or [Provider](references/provider.md) for Provider. Other recognized packages still require version/API verification against the integration contract; recognition is not a claim that a concrete template exists for every backend.

## What NOT to do

- For the Bloc backend, do not introduce event-based `Bloc`; use `Cubit`. Do not change the shared naming/data ownership contract when using a different backend.
- Do not put screens in `StatefulWidget` just to call `context.read<XCubit>().fetch()` in `initState`. The fetch belongs to owner creation; for Cubit this is the constructor.
- Do not name state variants without the `State` suffix (no `XInitial` — use `XInitialState`), and do not share one generic `XLoadingState` across methods — states are per method (`GetXLoadingState`, `AddXLoadingState`, …).
- Do not give a design-only screen's cubit sample-data fields, a fake fetch or a fake repository. Without an API it holds only UI interaction state; its sample content stays as literals in the widgets.
- Do not carry the fetched data in success states or read it from the state in the UI. Store it in a plain nullable field directly on the cubit — not a private field plus a public getter.
- Do not create a `TextEditingController` empty and fill it with `.text = ...` later when the cubit already has the initial value at construction time — pre-fill it in the constructor's initializer list instead.
