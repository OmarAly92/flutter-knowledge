import 'dart:async';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart' as riverpod;
import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';
import 'package:state_reference_check/contracts.dart';
import 'package:state_reference_check/cubit/x_cubit.dart' as bloc;
import 'package:state_reference_check/provider/x_cubit.dart' as change;
import 'package:state_reference_check/riverpod/x_cubit.dart' as river;
import 'package:state_reference_check/app_owner_listener.dart';

class DeferredRepository implements XRepository {
  final requests = <Completer<FetchResult>>[];
  @override
  Future<FetchResult> getX() {
    final request = Completer<FetchResult>();
    requests.add(request);
    return request.future;
  }
}
const loaded = FetchSuccess(GlobalResponse(data: XModel(name: 'sample')));

void main() {
  test('Cubit ignores completion after close and keeps owner model empty', () async {
    final repository = DeferredRepository();
    final owner = bloc.XCubit(repository);
    await owner.close();
    repository.requests.single.complete(loaded);
    await Future<void>.delayed(Duration.zero);
    expect(owner.xModel, isNull);
    expect(owner.state, isA<bloc.GetXLoadingState>());
  });

  test('Provider owner emits per-method states with payload-free success', () async {
    final repository = DeferredRepository();
    final owner = change.XCubit(repository);
    addTearDown(owner.dispose);
    expect(owner.state, isA<change.GetXLoadingState>());
    repository.requests.single.complete(loaded);
    await Future<void>.delayed(Duration.zero);
    expect(owner.state, isA<change.GetXSuccessState>());
    expect(owner.xModel?.name, 'sample');
    final failing = owner.getX();
    repository.requests.last.complete(const FetchFailure(Failure('offline')));
    await failing;
    expect(owner.state, isA<change.GetXFailureState>());
  });

  test('Provider owner drops late and superseded fetches', () async {
    final repository = DeferredRepository();
    final owner = change.XCubit(repository);
    final next = owner.getX();
    repository.requests.first.complete(const FetchSuccess(GlobalResponse(data: XModel(name: 'old'))));
    await Future<void>.delayed(Duration.zero);
    expect(owner.xModel, isNull);
    owner.dispose();
    repository.requests.last.complete(loaded);
    await next;
    expect(owner.xModel, isNull);
  });

  test('Riverpod route scopes own separate state holders', () async {
    final repository = DeferredRepository();
    final first = riverpod.ProviderContainer(overrides: [river.xCubitProvider.overrideWith(() => river.XCubit(repository))]);
    final second = riverpod.ProviderContainer(overrides: [river.xCubitProvider.overrideWith(() => river.XCubit(repository))]);
    addTearDown(first.dispose);
    addTearDown(second.dispose);
    final states = <river.XState>[];
    first.listen(river.xCubitProvider, (_, state) => states.add(state), fireImmediately: true);
    final firstOwner = first.read(river.xCubitProvider.notifier);
    final secondOwner = second.read(river.xCubitProvider.notifier);
    expect(identical(firstOwner, secondOwner), isFalse);
    await Future<void>.delayed(Duration.zero);
    expect(repository.requests.length, 2);
    repository.requests.first.complete(loaded);
    await Future<void>.delayed(Duration.zero);
    expect(states.map((state) => state.runtimeType), [river.XInitialState, river.GetXLoadingState, river.GetXSuccessState]);
    expect(firstOwner.xModel?.name, 'sample');
  });

  test('Riverpod completion after disposal cannot mutate owner-held data', () async {
    final repository = DeferredRepository();
    final container = riverpod.ProviderContainer(overrides: [river.xCubitProvider.overrideWith(() => river.XCubit(repository))]);
    container.read(river.xCubitProvider);
    final owner = container.read(river.xCubitProvider.notifier);
    await Future<void>.delayed(Duration.zero);
    container.dispose();
    repository.requests.single.complete(loaded);
    await Future<void>.delayed(Duration.zero);
    expect(owner.xModel, isNull);
  });

  testWidgets('Screen effect listener detaches from a still-live owner', (tester) async {
    final repository = DeferredRepository();
    final owner = change.XCubit(repository);
    addTearDown(owner.dispose);
    var effects = 0;
    await tester.pumpWidget(AppOwnerListener(owner: owner, onChange: () => effects++, child: const SizedBox()));
    repository.requests.first.complete(loaded);
    await tester.pumpAndSettle();
    expect(effects, 1);
    await tester.pumpWidget(const SizedBox());
    final next = owner.getX();
    repository.requests.last.complete(loaded);
    await next;
    expect(effects, 1);
  });

  testWidgets('Provider route owns disposal, selectors and Screen effect listener detach', (tester) async {
    final repository = DeferredRepository();
    var effects = 0;
    change.XState? renderedState;
    change.XCubit? owner;
    await tester.pumpWidget(ChangeNotifierProvider<change.XCubit>(
      create: (_) => owner = change.XCubit(repository),
      child: Builder(builder: (context) => AppOwnerListener(
        owner: context.read<change.XCubit>(),
        onChange: () => effects++,
        child: Selector<change.XCubit, change.XState>(
          selector: (_, cubit) => cubit.state,
          shouldRebuild: (_, next) => next is change.GetXLoadingState || next is change.GetXSuccessState || next is change.GetXFailureState,
          builder: (_, state, child) { renderedState = state; return const SizedBox(); },
        ),
      )),
    ));
    repository.requests.single.complete(loaded);
    await tester.pumpAndSettle();
    expect(effects, 1);
    expect(renderedState, isA<change.GetXSuccessState>());
    await tester.pumpWidget(const SizedBox());
    await owner!.getX();
    expect(repository.requests.length, 1);
    expect(effects, 1);
  });
}
