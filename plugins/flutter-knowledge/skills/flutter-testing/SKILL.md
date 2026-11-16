---
name: flutter-testing
description: Use when explicitly asked to write, add or update Flutter tests: unit tests for data sources, repositories or state owners, widget tests for screens, or integration tests of user flows. Visual snapshots use golden-tests.
---

# Flutter tests

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

**Repository tests**: mock the abstract data source and `NetworkStatus`. Group by method (matching the cubit's per-method state naming), covering these branches: offline → `Result.failure(ServerFailure.noNetwork())` without calling the data source; data source succeeds → `Result.success(...)`; data source throws a `Failure` → `Result.failure(error)`; data source throws anything else, or a payload field the repository checks is missing → `Result.failure` with a `MappingFailure` (`LocalFailure` for a device data source) — the last two only where the repository implements them.

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
      when(() => dataSource.getX()).thenAnswer((_) async => GlobalResponse(data: XModel(id: '1')));

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

## Widget tests

Only when the user asks for them. One file per screen or shared widget, mirroring `lib/`: `test/feature/<feature>/presentation/<screen>_screen/ui/<screen>_screen_test.dart`.

- Mount through the project's widget-test wrapper: `test/helpers/golden_harness.dart` when it exists, otherwise the themed wrapper from `flutter-app-theme` (`ScreenUtilInit` + `MaterialApp(theme: AppTheme.of(skin))` + the configured localization). A bare `MaterialApp` makes `context.tokens` throw.
- Provide the real cubit fed by a mocked repository, the way the route provides it (`BlocProvider(create: (_) => XCubit(repository), child: const XScreen())`); stub the repository before pumping, since the constructor fetch runs on creation.
- Find by what the user sees: the localized text (`find.text(LocaleKeys.trips_title.tr())`), the project wrapper type (`find.byType(PrimaryButton)`) or semantics. Add a `Key` to production code only when text and type are ambiguous, as a `const ValueKey('<screen>_<element>')`.
- `pump()` after a tap; `pump(duration)` with `tokens.motion`-length steps for animations. Avoid `pumpAndSettle` on screens with `AppLoader` or another endless animation: it never settles.
- Assert states and effects the screen owns: the success content, the `AppErrorWidget` on failure, a navigation or snackbar from the Screen listener.

## Integration tests

Only when the user asks for them. They run the real app on a device or emulator, so they follow the same run authorization as any app launch.

```
integration_test/<flow>_test.dart     # one user flow per file
test_driver/integration_test.dart     # host script for flutter drive
test_driver/app.dart                  # driver entry for flutter_driver / MCP exploration
```

- Add `integration_test` (and `flutter_driver` for the driver entry) as SDK dev dependencies only when creating these files.
- Each test calls `IntegrationTestWidgetsFlutterBinding.ensureInitialized()`, then starts the real startup with `app.main()` so DI, localization, cache and the router are the production ones. Ask before testing against a real backend; otherwise point the app at the project's existing test environment.
- The driver extension never goes in `lib/main.dart`. `test_driver/app.dart` enables it and calls the real entry point; run it with `flutter run -t test_driver/app.dart` to explore a flow through `flutter_driver_command` in the [Dart MCP server](../flutter-knowledge/references/dart-mcp.md), then write the steps that worked as an `integration_test/` test:

```dart
import 'package:flutter_driver/driver_extension.dart';
import 'package:<app>/main.dart' as app;

void main() {
  enableFlutterDriverExtension();
  app.main();
}
```

- Finders and pumping follow the widget-test rules above; scroll lazily built lists into view with `scrollUntilVisible` before tapping.

## What NOT to do

- Do not write unit, widget or integration tests unprompted. Only add them when the user explicitly asks.
- Do not enable the Flutter Driver extension in `lib/main.dart` or add test-only branches to production code.
- Do not change `lib/` code in a tests-only task. Test the code as it is, and report a convention gap you find (a repository without the final catch or payload check, for example) instead of fixing it, unless the user asked for the fix too.
- Use the configured mocking mechanism; `mocktail` is the default. If `mockito` is selected, use its verified generation/mocking workflow rather than introducing mocktail alongside it.
- For the Bloc backend with configured `bloc_test`, use `blocTest` rather than hand-written stream subscriptions. For another backend use its verified state observation/lifecycle through the configured test runner.
- Do not drop test files in a flat `test/` dir — mirror the `lib/feature/<feature>/...` tree under `test/`.
- Do not skip the offline branch when testing a repository method — assert `Result.failure(ServerFailure.noNetwork())` is returned and the data source is never called.
- Do not expect the constructor fetch's `...LoadingState` in `blocTest` — it is emitted inside `build()`, before `blocTest` listens. Assert a loading state only for a call made from `act:`.
