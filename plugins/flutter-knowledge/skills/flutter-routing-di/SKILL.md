---
name: flutter-routing-di
description: Flutter routing and dependency injection conventions — per-feature get_it injection files and dependency registration functions, core registrations in lib/core/di/injection.dart, registerAppDependencies in lib/app_injection.dart and its registration test, RoutesStrings constants, the lib/core/router/app_router.dart library whose case branches own the BlocProvider, registerFactoryParam with param1, MultiBlocProvider, BlocProvider.value for sharing a cubit, and the Navigation extension. Use before adding or editing a route, a BlocProvider, or a get_it registration in a Flutter project.
---

# Flutter routing & DI

For implementation, read the [project configuration contract](../flutter-init/references/configuration.md) before applying package-specific instructions. Keep its conventions and naming; adapt package-specific examples through the selected mechanics.

Invoked by the `flutter-knowledge` skill (or directly via `/flutter-routing-di`) before adding or editing a route, a `BlocProvider`, or a `get_it` registration. Related skills: `flutter-state-management` for the cubit being provided, `flutter-data-layer` for the repository and data source being registered, and `flutter-screen-ui` for the screen being routed to.

**These conventions are the source of truth.** Existing codebases may be old and inconsistent — where legacy code contradicts this skill, follow the skill and do NOT copy the legacy pattern.

## Dependency injection

The code below is the default get_it implementation. Keep feature-owned injection files, explicit dependency typing and lifetimes with another selected mechanism; replace registration/provider APIs only.

```
lib/core/di/injection.dart          # final GetIt sl = GetIt.instance; + registerCoreDependencies()
lib/feature/<feature>/<feature>_injection.dart   # register<Feature>Dependencies()
lib/app_injection.dart              # registerAppDependencies(): core first, then every feature
lib/main.dart                       # registerAppDependencies() once, before runApp
test/app_injection_test.dart        # asserts every type is registered
```

Each feature owns one injection file that registers its cubits, its repository and its data sources — nothing else:

```dart
import '../../core/di/injection.dart';

void register<Feature>Dependencies() {
  sl.registerFactory<<Screen>Cubit>(
    () => <Screen>Cubit(sl<<Feature>Repository>()),
  );

  sl.registerLazySingleton<<Feature>Repository>(
    () => <Feature>RepositoryImp(sl<<Feature>RemoteDataSource>(), sl<NetworkStatus>()),
  );

  sl.registerLazySingleton<<Feature>RemoteDataSource>(
    () => <Feature>RemoteDataSourceImp(sl<ApiConsumer>()),
  );
}
```

`lib/app_injection.dart` calls core first, then one line per feature:

```dart
void registerAppDependencies() {
  registerCoreDependencies();
  registerAuthDependencies();
  register<Feature>Dependencies();
}
```

- **A new feature** = a new `<feature>_injection.dart` + one line in `registerAppDependencies` + its cubits, repository and data sources in `test/app_injection_test.dart` (`expect(sl.isRegistered<XCubit>(), isTrue);` in the matching group). A UI-only feature's file registers just its cubit.
- **Cubits are factories** (one per route or composition owner); everything else is a **lazy singleton**. Use `registerFactoryParam` for a cubit that needs a constructor-time parameter. Singletons outlive the widget tree, so a cubit that subscribes to one must cancel in `close()`.
- **Explicit types everywhere**: `sl.registerFactory<XCubit>(…)`, `sl<XRepository>()` — never an inferred `sl()`.
- Define `final GetIt sl = GetIt.instance;` only in `lib/core/di/injection.dart`. Every file that registers or resolves dependencies imports that canonical file and uses global `sl` directly. Core, app and feature registration functions take no container parameter; widgets and routers never receive or store a locator. Do not shadow `sl` with a local or parameter. Service constructors still receive their actual typed dependencies.
- **Shared services register in core**, in `registerCoreDependencies`: network status, `ApiConsumer`, the database and its DAOs, session handling, and anything else in `lib/core/services/`. A feature never registers a core type.
- **`core/` never imports a feature** — the router is the one part of core that does. A core service never takes a feature type: if it needs feature data, it goes through a core type (a DAO, a core interface) the feature also uses. When a core interface's implementation needs a feature type, register that implementation in the feature's injection file.
- Tests import the same global `sl`, await `sl.reset()` before registering the graph, and await cleanup afterward; scopes may isolate overrides. Initialize required preferences/assets before `registerAppDependencies()`. Swap boundary fakes with awaited `sl.unregister<T>()` and typed registrations. Dispose widget-owned state before resetting services, and restore `Bloc.observer` in observer tests. Do not pass a custom GetIt instance into production code.

The Bloc root NetworkCubit is a core factory provided by normal `BlocProvider(create: ..., lazy: false)` in MyApp; that provider owns its close. Read the [network lifecycle contract](../flutter-core/references/core-contracts.md#root-network-ownership). Its active widget consumers read/watch the provider rather than resolving another factory instance. This does not change `.value` for sharing an existing screen owner.

## Routing

The named-Navigator library below is the default routing implementation. A different selected router keeps its route declarations and the project's navigation extension while preserving route-owned provisioning, explicit arguments and shared-owner semantics.

`lib/core/router/app_router.dart` is one library: `AppRouter` (`navigationKey`, `scaffoldMessengerKey`, `generateRoute`) plus two `part` files — `routes_strings.dart` (`RoutesStrings`, the route names) and `../helpers/extensions/router_extensions.dart` (the `Navigation` extension). Import `app_router.dart` to get route names and navigation; a part file cannot be imported on its own.

`AppRouter` owns the existing entry decision in public `static String get initialRoute`; MyApp only passes `AppRouter.initialRoute` to MaterialApp. A root-only router returns `RoutesStrings.root`. Do not add a private forwarding getter or invent auth/onboarding policy. Selected alternative routers preserve their verified entry mechanism.

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

The default `Navigation` part implements `Future<dynamic> pushNamed(String routeName, {Object? arguments})`, `Future<dynamic> pushReplacementNamed(String routeName, {Object? arguments})`, `Future<dynamic> pushNamedAndRemoveUntil(String routeName, RoutePredicate predicate, {Object? arguments})`, `void pop<T>([T? result])`, `void popUntil(RoutePredicate predicate)`, and `void popToRoot()`. Pushes, `popUntil` and `popToRoot` use `Navigator.of(this, rootNavigator: true)`; `pop<T>` uses `Navigator.pop(this, result)` so local pops retain their behavior. Forward arguments/predicates and return the push futures. Preserve additional working caller APIs where needed. Exercise nested/root routing, arguments and returned results with actual Navigators.

**Navigation** goes through the `Navigation` extension: `context.pushNamed(...)`, `context.pushReplacementNamed(...)`, `context.pushNamedAndRemoveUntil(name, (_) => false)`, `context.pop()`, `context.popUntil(...)`, `context.popToRoot()` — never raw `Navigator.of(context)` calls.

## What NOT to do

- Do not wrap the screen widget itself in `BlocProvider`. The provider lives in the `app_router.dart` route `case`.
- Do not register a feature's types in `lib/core/di/injection.dart`, or a core service in a feature's injection file.
- Do not import a feature from `core/` (other than the router), and do not give a core service a feature type as a dependency.
- Do not use inferred `sl()` lookups, create another container or pass/store a container on registration functions, widgets or routers. Import the canonical global `sl`; never shadow it.
- Do not add a feature's injection file without its line in `registerAppDependencies` and its types in `test/app_injection_test.dart`.
- Do not import `routes_strings.dart` or `router_extensions.dart` directly — import `app_router.dart`.
- Do not add a private constructor (`X._()`) to a static-only constants class (`EndPoints`, `RoutesStrings`, `AppFonts`, ...) to block instantiation — declare it `sealed class X` instead.
- Do not create a second cubit instance for a screen that should share an existing one — pass it and use `BlocProvider.value`.

Direct initialization in `lib/main.dart` and `MyApp` in `lib/my_app.dart` follow the [startup/router contract](../flutter-core/references/core-contracts.md#core-api-alignment), including the initial-route getter while preserving target startup policy; do not create a production bootstrap helper.
