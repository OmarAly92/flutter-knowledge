# Riverpod under the same state contract

Use for the Riverpod family after checking the installed version. The owner/provisioning recipe is analyzed and exercised under Riverpod 2.6.1 and 3.4.3 by `tests/check_state_references.py`. This manual NotifierProvider pattern needs no generator. Keep XState in the existing part file, with the same sealed/equality/per-method variants. Repository, model, response and Failure types below are existing project contracts.

Use Notifier<XState>, not AsyncNotifier<XModel> or model-bearing AsyncValue as public application state. The owner stays XCubit, xModel stays a public nullable owner field, and success states remain payload-free.

```dart
class XCubit extends Notifier<XState> {
  XCubit(this._repository);

  final XRepository _repository;
  XModel? xModel;
  bool _alive = false;
  int _epoch = 0;
  int _request = 0;

  @override
  XState build() {
    _alive = true;
    xModel = null;
    _request = 0;
    final epoch = ++_epoch;
    ref.onDispose(() {
      _alive = false;
      _epoch++;
    });
    Future<void>.microtask(() async {
      if (_alive && epoch == _epoch && _request == 0) {
        await getX();
      }
    });
    return const XInitialState();
  }

  Future<void> getX() async {
    if (!_alive) return;
    final epoch = _epoch;
    final request = ++_request;
    state = const GetXLoadingState();
    final result = await _repository.getX();
    if (!_alive || epoch != _epoch || request != _request) return;
    result.when(
      onSuccess: (response) {
        xModel = response.data;
        state = const GetXSuccessState();
      },
      onFailure: (failure) => state = GetXFailureState(failure: failure),
    );
  }
}
```

The epoch prevents an older provider lifecycle accepting a late result. The request guard is a latest-fetch policy; writes need their own overlap decision. Keep controllers as field/initializer-list values and register their disposal in owner lifecycle. For controller-bearing owners, refresh through methods; replacing the owner requires a fresh route scope/factory rather than reusing disposed controllers through provider invalidation.

## Route-owned provisioning

Define this typed provider in the feature's injection/composition file. The fallback requires a route override rather than creating an owner elsewhere:

```dart
final xCubitProvider = NotifierProvider<XCubit, XState>(
  () => throw StateError('The route must provide XCubit'),
);
```

At the route boundary, wrap the StatelessWidget Screen in ProviderScope using `xCubitProvider.overrideWith(() => XCubit(repository))`. Resolve arguments/repository through configured DI and navigation. Separate route scopes get separate owners. Do not create the owner in Screen.build or add a second DI container unasked.

Inside a Consumer wrapped by the StatelessWidget Screen, use `ref.listen(xCubitProvider, ...)` for exact success/failure effects. The StatelessWidget Body uses Consumer plus `ref.watch(xCubitProvider.select(...))` to select its operation states. Retain the last relevant operation state when excluding other operations; do not select a constant success type that hides loading→success transitions. Read model data from `ref.read(xCubitProvider.notifier).xModel` while operation state supplies reactivity. Watching owner identity alone does not observe field mutation.

Test initial loading timing, success/failure, completion after disposal and superseded fetches. Dispose ProviderContainer in teardown and check the installed container-listening API.

Primary APIs: [NotifierProvider](https://pub.dev/documentation/riverpod/latest/riverpod/NotifierProvider-class.html), [lifecycle](https://riverpod.dev/docs/concepts2/auto_dispose).
