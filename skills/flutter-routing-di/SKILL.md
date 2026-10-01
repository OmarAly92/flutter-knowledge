---
name: flutter-routing-di
description: Flutter routing and dependency injection conventions — per-feature get_it injection files (`<feature>_injection.dart` with `register<Feature>Dependencies(GetIt sl)`), core registrations in lib/core/di/injection.dart, registerAppDependencies in lib/app_injection.dart and its registration test, RoutesStrings constants, the lib/core/router/app_router.dart library whose case branches own the BlocProvider, registerFactoryParam with param1, MultiBlocProvider, BlocProvider.value for sharing a cubit, and the Navigation extension. Use before adding or editing a route, a BlocProvider, or a get_it registration in a Flutter project.
---

# Flutter routing & DI

Invoked by the `flutter-knowledge` skill (or directly via `/flutter-routing-di`) before adding or editing a route, a `BlocProvider`, or a `get_it` registration. Related skills: `flutter-cubit` for the cubit being provided, `flutter-data-layer` for the repository and data source being registered, and `flutter-screen-ui` for the screen being routed to.

**These conventions are the source of truth.** Existing codebases may be old and inconsistent — where legacy code contradicts this skill, follow the skill and do NOT copy the legacy pattern.

## Dependency injection (get_it, per feature)

```
lib/core/di/injection.dart          # final GetIt sl = GetIt.instance; + registerCoreDependencies(GetIt sl)
lib/feature/<feature>/<feature>_injection.dart   # register<Feature>Dependencies(GetIt sl)
lib/app_injection.dart              # registerAppDependencies(GetIt sl): core first, then every feature
lib/main.dart                       # registerAppDependencies(sl) once, before runApp
test/app_injection_test.dart        # asserts every type is registered
```

Each feature owns one injection file that registers its cubits, its repository and its data sources — nothing else:

```dart
import 'package:get_it/get_it.dart';

void register<Feature>Dependencies(GetIt sl) {
  /// Blocs
  sl.registerFactory<<Screen>Cubit>(
    () => <Screen>Cubit(sl<<Feature>Repository>()),
  );

  /// Repository
  sl.registerLazySingleton<<Feature>Repository>(
    () => <Feature>RepositoryImp(sl<<Feature>RemoteDataSource>(), sl<NetworkStatus>()),
  );

  /// Data Sources
  sl.registerLazySingleton<<Feature>RemoteDataSource>(
    () => <Feature>RemoteDataSourceImp(sl<ApiConsumer>()),
  );
}
```

`lib/app_injection.dart` calls core first, then one line per feature:

```dart
void registerAppDependencies(GetIt sl) {
  registerCoreDependencies(sl);
  registerAuthDependencies(sl);
  register<Feature>Dependencies(sl);   // ← a new feature adds one line here
}
```

- **A new feature** = a new `<feature>_injection.dart` + one line in `registerAppDependencies` + its cubits, repository and data sources in `test/app_injection_test.dart` (`expect(locator.isRegistered<XCubit>(), isTrue);` in the matching group). A UI-only feature's file registers just its cubit.
- **Cubits are factories** (one per route); everything else is a **lazy singleton**. Use `registerFactoryParam` for a cubit that needs a constructor-time parameter. Singletons outlive the widget tree, so a cubit that subscribes to one must cancel in `close()`.
- **Explicit types everywhere**: `sl.registerFactory<XCubit>(…)`, `sl<XRepository>()` — never an inferred `sl()`.
- The function takes the locator as a parameter (`GetIt sl`) and registers into it, so tests can pass `GetIt.asNewInstance()`. Never reach for `GetIt.instance` inside a register function.
- **Shared services register in core**, in `registerCoreDependencies`: network status, `ApiConsumer`, the database and its DAOs, sockets, session/logout, and anything else in `lib/core/services/`. A feature never registers a core type.
- **`core/` never imports a feature** — the router is the one part of core that does. A core service never takes a feature type: if it needs feature data, it goes through a core type (a DAO, a core interface) the feature also uses. When a core interface's implementation needs a feature type, register that implementation in the feature's injection file.
- A widget test that needs the real graph does `await sl.reset(); registerAppDependencies(sl);`, then swaps fakes in with `sl.unregister<T>()` + `sl.register…<T>(…)`.

## Routing

`lib/core/router/app_router.dart` is one library: `AppRouter` (`navigationKey`, `scaffoldMessengerKey`, `generateRoute`) plus two `part` files — `routes_strings.dart` (`RoutesStrings`, the route names) and `../helpers/extensions/router_extensions.dart` (the `Navigation` extension). Import `app_router.dart` to get route names and navigation; a part file cannot be imported on its own.

A new route = a `RoutesStrings` constant + a `case` in `AppRouter.generateRoute`. `RoutesStrings` is a `sealed class` of static route constants — no private constructor (static-only classes are `sealed class X { ... }`, never `X._()`). **The `case` body is where `BlocProvider` lives** — NOT inside the screen widget:

```dart
case RoutesStrings.xScreen:
  return MaterialPageRoute(
    builder: (context) {
      return BlocProvider(
        create: (context) => sl<XCubit>(),
        child: const XScreen(),
      );
    },
  );
```

For `registerFactoryParam` cubits, pass the route argument via `param1`:

```dart
create: (context) => sl<XCubit>(param1: settings.arguments as ParamType),
```

For screens needing multiple cubits, use `MultiBlocProvider` (mirror an existing multi-cubit route in `app_router.dart`).

To share one cubit across two navigated screens, pass the existing instance via route arguments and wrap the second screen's route in `BlocProvider.value(value: cubit, …)` — never create a second instance.

**Navigation** goes through the `Navigation` extension: `context.pushNamed(...)`, `context.pushReplacementNamed(...)`, `context.pushNamedAndRemoveUntil(name, (_) => false)`, `context.pop()`, `context.popUntil(...)`, `context.popToRoot()` — never raw `Navigator.of(context)` calls.

## What NOT to do

- Do not wrap the screen widget itself in `BlocProvider`. The provider lives in the `app_router.dart` route `case`.
- Do not register a feature's types in `lib/core/di/injection.dart`, or a core service in a feature's injection file.
- Do not import a feature from `core/` (other than the router), and do not give a core service a feature type as a dependency.
- Do not use inferred `sl()` lookups, and do not register into `GetIt.instance` from inside a register function.
- Do not add a feature's injection file without its line in `registerAppDependencies` and its types in `test/app_injection_test.dart`.
- Do not import `routes_strings.dart` or `router_extensions.dart` directly — import `app_router.dart`.
- Do not add a private constructor (`X._()`) to a static-only constants class (`EndPoints`, `RoutesStrings`, `AppFonts`, ...) to block instantiation — declare it `sealed class X` instead.
- Do not create a second cubit instance for a screen that should share an existing one — pass it and use `BlocProvider.value`.
