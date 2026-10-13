# Provider under the same state contract

The owner, Selector and effects lifecycle recipe is checked with Provider 6.1.5+1. Verify installed APIs before adapting it to another version. Keep the XState part file, sealed/equality/per-method variants and existing project data contracts. XCubit remains the owner name; ChangeNotifier changes notification mechanics, not naming or payload placement.

```dart
class XCubit extends ChangeNotifier {
  XCubit(this._repository) {
    getX();
  }

  final XRepository _repository;
  XModel? xModel;
  XState state = const XInitialState();
  bool _disposed = false;
  int _request = 0;

  Future<void> getX() async {
    if (_disposed) return;
    final request = ++_request;
    _emit(const GetXLoadingState());
    final result = await _repository.getX();
    if (_disposed || request != _request) return;
    result.when(
      onSuccess: (response) {
        xModel = response.data;
        _emit(const GetXSuccessState());
      },
      onFailure: (failure) => _emit(GetXFailureState(failure: failure)),
    );
  }

  void _emit(XState next) {
    if (_disposed) return;
    state = next;
    notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    _request++;
    super.dispose();
  }
}
```

Controllers/form fields remain on this owner, initialized/prefilled as prescribed. Dispose resources after marking the owner disposed and before super.dispose. Latest-result suppression fits this fetch; writes need their own overlap policy.

## Provisioning and UI

At the route boundary use `ChangeNotifierProvider<XCubit>(create: (_) => XCubit(repository), child: const XScreen())`. It owns that new notifier. Use `.value` only to share an existing owner, whose creating route retains lifetime responsibility. Keep per-feature registration files and explicit dependencies with the chosen DI mechanism.

The StatelessWidget Body uses `Selector<XCubit, XState>` selecting `owner.state`, with `shouldRebuild` naming exact GetX loading/success/failure variants. Its builder reads model data from the same owner. Selecting owner identity or only a loaded boolean misses relevant transitions.

Effects remain outside builders, in the StatelessWidget Screen's listening wrapper. Reuse the existing effects primitive. If the backend needs one, [the Listenable effects reference](listenable-effects.md) supplies a real core subscription primitive; do not import that class before its file exists. Its internal widget State owns only subscription plumbing, as framework listener widgets do. Application state, data, fetches and input controllers remain on XCubit.

Test operation sequences, failure, completion after disposal, selective rebuilding and listener cleanup. [Provider lifecycle API](https://pub.dev/documentation/provider/latest/provider/ChangeNotifierProvider-class.html).
