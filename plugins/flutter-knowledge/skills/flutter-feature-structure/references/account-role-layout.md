# Account-role layout

Read this before placing, naming, routing or wiring any file in an app with two or more account roles. It extends `flutter-feature-structure`, `flutter-routing-di` and `add-translation`; their other rules still apply.

## Folders and names

Use it when the app has two or more **account roles that each get their own interface after login** (client and owner, driver and rider, student and teacher). Evidence: the design has a separate set of screens per role, the API returns a role or user type that decides where the user lands, or the request says so. Permissions inside one shared interface (an admin sees an extra button) are not separate roles; keep the flat layout. When the evidence is unclear, ask before choosing.

```
lib/feature/
  global/            # everything before login + every feature two or more roles use
    splash/
    onboarding/
    auth/
    chat/            # used by client and owner
  client/            # one folder per account role, snake_case, named as the business/backend names it
    app_nav_bar/
    home/
    orders/
  owner/
    app_nav_bar/
    home/
    properties/
```

- Every feature, in `global/` or a role folder, uses the feature tree from `flutter-feature-structure`.
- **`global/`** holds the pre-login features (splash, onboarding, auth and its sub-flows) and every feature two or more roles use. One implementation: where roles differ slightly, the screen reads the role from its cubit or route params rather than being copied per role. A role feature moves to `global/` when a second role starts using it.
- **A role folder** holds only the features that role uses; its tab shell is its own `app_nav_bar/` (see Routing and DI below).
- **Role prefix.** Inside `lib/feature/<role>/<feature>/` the folder keeps the plain feature name, but every name derived from the feature or a screen starts with the role: `client/home/` → `client_home_injection.dart` with `registerClientHomeDependencies()`, `client_home_remote_data_source.dart`, `client_home_repository.dart`, `presentation/client_home_screen/` with `ClientHomeScreen`, `ClientHomeBody`, `ClientHomeCubit` and its state classes, route `RoutesStrings.clientHome`, translation group `clientHome`. Models, params and section widgets keep their own names; prefix one only when the same name exists in another role and both meet in one file. `global/` features are not prefixed (`AuthCubit`, group `auth`).
- Widgets and helpers shared by features of different roles follow the usual rule: `lib/core/widgets/<purpose>/` and `lib/core/helpers/`. The account role itself is the core `AppRole` enum (see Routing and DI below).
- **Never mix layouts.** A project with `lib/feature/global/` puts every new feature under `global/` or a role folder, never directly under `lib/feature/`. A flat project that gains a second role keeps working in its layout until the user approves moving to this one; that move is its own change.

## Routing and DI

- **The role is a core enum**, `lib/core/helpers/app_role.dart`, one value per role folder, mapped from the backend value. The auth repository caches the role with `CacheHelper` under `CacheKeys.userRole` when it saves the session (the token stays in `SecureCacheHelper`), and logout removes both.

```dart
enum AppRole {
  client('client'),
  owner('owner');

  const AppRole(this.apiValue);

  final String apiValue;

  static AppRole? fromApi(String? value) {
    for (final role in values) {
      if (role.apiValue == value) return role;
    }
    return null;
  }
}
```

- **`AppRouter` owns where each role lands**: a public `static String homeFor(AppRole role)` switch returning each role's entry route (its nav bar shell, `RoutesStrings.clientAppNavBar`), and `initialRoute` sends a user with a session and a cached role to `homeFor(role)`, everyone else to the existing global entry (splash, onboarding or auth). A missing or unknown role goes to auth, never to a guessed role.
- **After login**, the auth repository has already checked that the role is known (`AppRole.fromApi` returned a value) and cached it; the cubit holds the user, its success state stays payload-free, and the auth screen's listener navigates `context.pushNamedAndRemoveUntil(AppRouter.homeFor(cubit.role!), (_) => false)`. Logout navigates to auth the same way.
- **Each role with tabs has its own shell** from the [app nav bar recipe](../../flutter-routing-di/references/app-nav-bar.md) at `lib/feature/<role>/app_nav_bar/`, with every recipe name role-prefixed.
- **DI and routes follow the role prefix**: `lib/feature/client/home/client_home_injection.dart` declares `registerClientHomeDependencies()`, and the route is `RoutesStrings.clientHome`. `registerAppDependencies` calls core, then the `global/` features, then each role's features, grouped by role; `test/app_injection_test.dart` has one group per role. Every role's dependencies are registered at startup; cubits are factories, so an unused role costs nothing.
- **Nav bar recipe names** take the role prefix: `client_app_nav_bar_injection.dart`, `client_app_nav_bar_screen/`, `ClientAppNavBarCubit`, `ClientAppNavBarScreen`, `ClientAppNavTab`, `RoutesStrings.clientAppNavBar`, translation group `clientAppNavBar`.
- **Translation groups**: a role feature's group carries its role (`lib/feature/client/home/` → `"clientHome"`); a `global/` feature's group is its folder (`auth`).
