---
name: flutter-testing
description: Unit test conventions for a Flutter feature — mocktail mocks, bloc_test cubit tests, data source/repository/cubit test layout and coverage. Use when the user explicitly asks to write, add, or update tests for a Flutter feature.
---

# Unit tests

Invoked by the `flutter-knowledge` skill (or directly via `/flutter-testing`) only when the user explicitly asks for tests — never generate test files as a side effect of scaffolding a feature.

Tooling: `mocktail` for mocks, `bloc_test` for cubit tests. Add both to `dev_dependencies` in `pubspec.yaml` if not already present.

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

**Cubit tests**: mock the repository, use `blocTest` per method. Because the cubit fires its initial fetch from the constructor, stub the repository's response *before* calling `build:` — `blocTest` subscribes to the stream as soon as `build()` returns, in time to catch the states that fetch emits.

```dart
class MockXRepository extends Mock implements XRepository {}

void main() {
  late MockXRepository repository;

  setUp(() => repository = MockXRepository());

  group('getX', () {
    blocTest<XCubit, XState>(
      'emits [GetXLoadingState, GetXSuccessState] when getX succeeds',
      setUp: () => when(() => repository.getX())
          .thenAnswer((_) async => Result.success(GlobalResponse(data: XModel()))),
      build: () => XCubit(repository),
      expect: () => [const GetXLoadingState(), const GetXSuccessState()],
    );

    blocTest<XCubit, XState>(
      'emits [GetXLoadingState, GetXFailureState] when getX fails',
      setUp: () => when(() => repository.getX())
          .thenAnswer((_) async => Result.failure(ServerFailure(message: 'error'))),
      build: () => XCubit(repository),
      expect: () => [const GetXLoadingState(), isA<GetXFailureState>()],
    );
  });
}
```

## What NOT to do

- Do not write unit tests unprompted. Only add them when the user explicitly asks.
- Do not use `mockito`/`@GenerateMocks` or hand-rolled fakes for new tests — use `mocktail`.
- Do not test a cubit with plain `test()` + manual `cubit.stream` listening — use `blocTest` from `bloc_test`.
- Do not drop test files in a flat `test/` dir — mirror the `lib/feature/<feature>/...` tree under `test/`.
- Do not skip the offline branch when testing a repository method — assert `Result.failure(ServerFailure.noNetwork())` is returned and the data source is never called.
