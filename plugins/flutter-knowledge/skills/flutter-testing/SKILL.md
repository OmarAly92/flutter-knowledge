---
name: flutter-testing
description: Use when explicitly asked to write, add or update Flutter feature unit tests for data sources, repositories or state owners. Visual snapshots use golden-tests.
---

# Unit tests

For implementation, read the [project configuration contract](../flutter-init/references/configuration.md) before applying package-specific instructions. Keep its conventions and naming; adapt package-specific examples through the selected mechanics.

Invoked by the `flutter-knowledge` skill (or directly via `/flutter-testing`) only when the user explicitly asks for tests — never generate test files as a side effect of scaffolding a feature.

Tooling comes from `packages.mocking` and `packages.state_testing`. The examples below use the default `mocktail` / `bloc_test` combination. Add only the selected dependencies needed for explicitly requested tests; for another state backend, verify a compatible observation harness.

**Layout**: tests mirror the `lib/` feature tree under `test/`, one `_test.dart` per source file:

```
test/feature/<feature>/
  data/
    data_source/<feature>_remote_data_source_test.dart
    repository/<feature>_repository_test.dart
  presentation/
    <screen>_screen/logic/<screen>_cubit_test.dart
```

**Mocktail mocks**: declare `class MockX extends Mock implements X {}` per collaborator, at the top of the test file. Register a fallback value in `setUpAll` before using `any()` for any non-primitive argument type — mocktail throws otherwise.

**Data source tests**: mock `ApiConsumer`, stub its `get`/`post`/etc. call, and assert the returned model is parsed correctly and that params were passed through `.toJson()` as the request body/query.

**Repository tests**: mock the abstract data source and `NetworkStatus`. Group by method (matching the cubit's per-method state naming), covering three branches: offline → `Result.failure(ServerFailure.noNetwork())` without calling the data source; data source succeeds → `Result.success(...)`; data source throws a `Failure` → `Result.failure(error)`.

```dart
class MockXRemoteDataSource extends Mock implements XRemoteDataSource {}
class MockNetworkStatus extends Mock implements NetworkStatus {}

void main() {
  late XRepositoryImp repository;
  late MockXRemoteDataSource dataSource;
  late MockNetworkStatus networkStatus;

  setUp(() {
    dataSource = MockXRemoteDataSource();
    networkStatus = MockNetworkStatus();
    repository = XRepositoryImp(dataSource, networkStatus);
  });

  group('getX', () {
    test('returns failure without calling the data source when offline', () async {
      when(() => networkStatus.isConnected).thenAnswer((_) async => false);

      final result = await repository.getX();

      expect(result, Result.failure(ServerFailure.noNetwork()));
      verifyNever(() => dataSource.getX());
    });

    test('returns success when the data source call succeeds', () async {
      when(() => networkStatus.isConnected).thenAnswer((_) async => true);
      when(() => dataSource.getX()).thenAnswer((_) async => GlobalResponse(data: XModel()));

      final result = await repository.getX();

      expect(result, isA<Success>());
    });
  });
}
```

**Cubit tests**: mock the repository, use `blocTest` per method, and stub the repository in `setUp:` so the stub is in place before `build:` constructs the cubit. A cubit that fires its initial fetch from the constructor emits `GetXLoadingState` synchronously inside `build()`, before `blocTest` subscribes to the stream, so that state is never recorded — expect only the states that follow it. To assert the loading state, let the initial fetch settle, call the method again from `act:`, and `skip:` the initial fetch's result.

```dart
class MockXRepository extends Mock implements XRepository {}

void main() {
  late MockXRepository repository;

  setUp(() => repository = MockXRepository());

  group('getX', () {
    blocTest<XCubit, XState>(
      'emits [GetXSuccessState] when the initial getX succeeds',
      setUp: () => when(() => repository.getX())
          .thenAnswer((_) async => Result.success(GlobalResponse(data: XModel()))),
      build: () => XCubit(repository),
      expect: () => [const GetXSuccessState()],
    );

    blocTest<XCubit, XState>(
      'emits [GetXFailureState] when the initial getX fails',
      setUp: () => when(() => repository.getX())
          .thenAnswer((_) async => Result.failure(ServerFailure(message: 'error'))),
      build: () => XCubit(repository),
      expect: () => [isA<GetXFailureState>()],
    );

    blocTest<XCubit, XState>(
      'emits [GetXLoadingState, GetXSuccessState] when getX is called again',
      setUp: () => when(() => repository.getX())
          .thenAnswer((_) async => Result.success(GlobalResponse(data: XModel()))),
      build: () => XCubit(repository),
      act: (cubit) async {
        await Future<void>.delayed(Duration.zero); // let the constructor's fetch settle
        await cubit.getX();
      },
      skip: 1, // the constructor fetch's GetXSuccessState
      expect: () => [const GetXLoadingState(), const GetXSuccessState()],
    );
  });
}
```

## What NOT to do

- Do not write unit tests unprompted. Only add them when the user explicitly asks.
- Use the configured mocking mechanism; `mocktail` is the default. If `mockito` is selected, use its verified generation/mocking workflow rather than introducing mocktail alongside it.
- For the Bloc backend with configured `bloc_test`, use `blocTest` rather than hand-written stream subscriptions. For another backend use its verified state observation/lifecycle through the configured test runner.
- Do not drop test files in a flat `test/` dir — mirror the `lib/feature/<feature>/...` tree under `test/`.
- Do not skip the offline branch when testing a repository method — assert `Result.failure(ServerFailure.noNetwork())` is returned and the data source is never called.
- Do not expect the constructor fetch's `...LoadingState` in `blocTest` — it is emitted inside `build()`, before `blocTest` listens. Assert a loading state only for a call made from `act:`.
