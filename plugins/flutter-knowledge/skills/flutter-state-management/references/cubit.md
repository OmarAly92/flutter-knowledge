# Cubit implementation reference

Use with configured `flutter_bloc` / `bloc`. The parent skill owns all naming and lifecycle rules; these examples show the default mechanisms. Use the configured equality implementation for state value comparison.

```dart
class XCubit extends Cubit<XState> {
  XCubit(this._repository) : super(const XInitialState()) {
    getX();
  }

  final XRepository _repository;

  XModel? xModel;

  Future<void> getX() async {
    if (isClosed) return;
    emit(const GetXLoadingState());
    final result = await _repository.getX();
    if (isClosed) return;
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
