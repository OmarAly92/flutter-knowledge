---
name: flutter-cubit
description: Flutter Cubit state management conventions — Cubit (never Bloc), sealed state classes with final class variants and Equatable, part/part of files, per-method `...State` naming, initial fetch in the constructor, data in a plain nullable cubit field, controllers as field initializers or initializer-list prefill, disposal in close(). Use before writing or editing a cubit or state class in a Flutter project.
---

# Flutter Cubit

Invoked by the `flutter-knowledge` skill (or directly via `/flutter-cubit`) before writing or editing any `*_cubit.dart` or `*_state.dart`. Related skills: `flutter-data-layer` for the repository the cubit calls, `flutter-routing-di` for registering the cubit and passing constructor parameters, `flutter-screen-ui` for how the UI consumes it, and `flutter-testing` when the user asks for cubit tests.

**These conventions are the source of truth.** Existing codebases may be old and inconsistent — where legacy code contradicts this skill, follow the skill and do NOT copy the legacy pattern.

## State management (Cubit)

- Use `Cubit` — never `flutter_bloc`'s full `Bloc` / event classes.
- State classes: sealed base class, `final class` variants, Equatable with `props`. The state file is a `part` of the cubit file: `part 'x_state.dart';` in the cubit, `part of 'x_cubit.dart';` in the state.
- **State naming**: every variant must end with the `State` suffix, and states are **per cubit method**: one shared `XInitialState`, then `<Method>LoadingState`, `<Method>SuccessState`, `<Method>FailureState` for each method (e.g. `GetOrdersLoadingState`). Failure states carry the `Failure` payload. The legacy `XInitial` form (no suffix) exists in old files — do NOT copy it.
- **Cubit owns its data lifecycle**: if the cubit has a fetch that should run when the screen opens, call it from the cubit's constructor body — never from a `StatefulWidget.initState`.
- **Cubit stores the data, not the state**: keep the response model in a plain nullable field directly on the cubit (`XModel? xModel;`) so the UI can read it after the success emit — success states stay payload-free. Don't wrap it in a private field plus a public getter (`_xModel` + `get xModel`) — that's boilerplate for no benefit here; a direct field is simpler.
- **All widget state lives on the cubit**: `TextEditingController`s, `ScrollController`s, form keys, dropdown/picker selections — declared as direct field initializers (`final nameController = TextEditingController();`), not assigned inside the constructor body. When the cubit receives existing data to edit (e.g. an initial model passed in via `registerFactoryParam`), pre-fill each controller with that value directly — `TextEditingController(text: initialModel.name)` — assigned through the constructor's initializer list; never construct it empty and set `.text` afterwards. Dispose disposables in cubit `close()`.

```dart
class XCubit extends Cubit<XState> {
  XCubit(this._repository) : super(const XInitialState()) {
    getX();          // ← initial fetch lives here
  }

  final XRepository _repository;

  XModel? xModel;

  Future<void> getX() async {
    emit(const GetXLoadingState());
    final result = await _repository.getX();
    result.when(
      onSuccess: (response) {
        xModel = response.data;
        emit(const GetXSuccessState());
      },
      onFailure: (failure) => emit(GetXFailureState(failure: failure)),
    );
  }
}
```

A cubit that edits existing data pre-fills its controllers from the initial model, via the initializer list:

```dart
class EditXCubit extends Cubit<EditXState> {
  EditXCubit(this._repository, XModel initialModel)
      : nameController = TextEditingController(text: initialModel.name),
        super(const EditXInitialState());

  final XRepository _repository;
  final TextEditingController nameController;

  @override
  Future<void> close() {
    nameController.dispose();
    return super.close();
  }
}
```

## What NOT to do

- Do not introduce `flutter_bloc`'s full `Bloc` / event classes — always `Cubit`.
- Do not put screens in `StatefulWidget` just to call `context.read<XCubit>().fetch()` in `initState`. The fetch belongs in the cubit constructor.
- Do not name state variants without the `State` suffix (no `XInitial` — use `XInitialState`), and do not share one generic `XLoadingState` across methods — states are per method (`GetXLoadingState`, `AddXLoadingState`, …).
- Do not carry the fetched data in success states or read it from the state in the UI. Store it in a plain nullable field directly on the cubit — not a private field plus a public getter.
- Do not create a `TextEditingController` empty and fill it with `.text = ...` later when the cubit already has the initial value at construction time — pre-fill it in the constructor's initializer list instead.
