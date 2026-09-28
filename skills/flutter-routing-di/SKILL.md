---
name: flutter-routing-di
description: Flutter routing and dependency injection conventions — RoutesStrings constants, app_router.dart case branches that own the BlocProvider, registerFactoryParam with param1, MultiBlocProvider, BlocProvider.value for sharing a cubit, and get_it service locator `_<feature>FeatureSetup()` methods. Use before adding or editing a route, a BlocProvider, or a service-locator registration in a Flutter project.
---

# Flutter routing & DI

Invoked by the `flutter-knowledge` skill (or directly via `/flutter-routing-di`) before adding or editing a route, a `BlocProvider`, or a `get_it` registration. Related skills: `flutter-cubit` for the cubit being provided, `flutter-data-layer` for the repository and data source being registered, and `flutter-screen-ui` for the screen being routed to and for the navigation extensions.

**These conventions are the source of truth.** Existing codebases may be old and inconsistent — where legacy code contradicts this skill, follow the skill and do NOT copy the legacy pattern.

## Service locator (DI)

Manual `get_it` in `lib/core/utils/service_locator.dart`. New features get a dedicated static method called from `init()` — do NOT inline registrations into `init()`. (Existing inline registrations for older features stay as they are.)

```dart
class ServiceLocator {
  static Future<void> init() async {
    // ... existing inline registrations stay ...
    _xFeatureSetup();          // ← add this call
  }

  static void _xFeatureSetup() {
    /// Blocs
    sl.registerFactory<<Screen>Cubit>(() => <Screen>Cubit(sl<<Feature>Repository>()));

    /// Repository
    sl.registerLazySingleton<<Feature>Repository>(
      () => <Feature>RepositoryImp(sl<<Feature>RemoteDataSource>(), sl<NetworkStatus>()),
    );

    /// Data Sources
    sl.registerLazySingleton<<Feature>RemoteDataSource>(
      () => <Feature>RemoteDataSourceImp(sl<ApiConsumer>()),
    );
  }
}
```

Register Cubits as factories (one per route); use `registerFactoryParam` for cubits needing a constructor-time parameter.

## Routing

Routes are wired in `lib/core/app_routes/routes_strings.dart` (route constant) and `lib/core/app_routes/app_router.dart` (`case` branch). `RoutesStrings` is a `sealed class` of static route constants — no private constructor needed (static-only classes are `sealed class X { ... }`, never `X._()`). **The `case` body is where `BlocProvider` lives** — NOT inside the screen widget:

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
create: (context) => sl<XCubit>(param1: argument as ParamType),
```

For screens needing multiple cubits, use `MultiBlocProvider` (mirror an existing multi-cubit route in `app_router.dart`).

To share one cubit across two navigated screens, pass the existing instance via route arguments and wrap the second screen's route in `BlocProvider.value(value: cubit, …)` — never create a second instance.

**Navigation**: `context.pushNamed(...)`, `context.pushReplacementNamed(...)`, `context.pushNamedAndRemoveUntil(name, (_) => false)`, `context.pop()` — never raw `Navigator.of(context)` calls.

## What NOT to do

- Do not wrap the screen widget itself in `BlocProvider`. The provider lives in `app_router.dart`.
- Do not inline new service-locator registrations into `init()`. Put them in a `_<feature>FeatureSetup()` static method and call it from `init()`.
- Do not add a private constructor (`X._()`) to a static-only constants class (`EndPoints`, `RoutesStrings`, `AppColors`, ...) to block instantiation — declare it `sealed class X` instead.
- Do not create a second cubit instance for a screen that should share an existing one — pass it and use `BlocProvider.value`.
