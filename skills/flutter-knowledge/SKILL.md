---
name: flutter-knowledge
description: Use anytime Flutter or Dart is mentioned, or for any task touching a Flutter project — writing, editing, reviewing, debugging, explaining, or scaffolding screens, widgets, cubits, blocs, state classes, models, data sources, repositories, routing, dependency injection, styling, theming, or localization in a .dart file or pubspec.yaml.
---

# Flutter knowledge

Full-stack Flutter conventions: architecture, data layer, state management, DI, routing, and UI rules.

**These conventions are the source of truth.** Existing codebases may be old and inconsistent — where legacy code contradicts this skill, follow the skill and do NOT copy the legacy pattern.

## Feature architecture

Features live under `lib/features/<feature>/` (snake_case — plural `features`, NOT `feature`). Every feature follows this tree — the presentation screen directory MUST be suffixed `_screen`:

```
data/
  data_source/<feature>_remote_data_source.dart
  model/                                  # add models as needed
  model/params/                           # request params classes
  repository/<feature>_repository.dart
presentation/
  <screen>_screen/                        # NOTE the _screen suffix
    logic/
      <screen>_cubit.dart
      <screen>_state.dart
    ui/
      <screen>_screen.dart
      widgets/
```

Omit `data/` entirely for UI-only features.

Before writing each file, read the equivalent file from an existing feature in the current codebase and mirror its style and import order. Do not invent a different shape:
- Cubit: pick an existing `*_cubit.dart` — note it kicks off the initial fetch from inside the constructor body, NOT from the screen's lifecycle.
- State: pick an existing `*_state.dart` — sealed class, `final class` variants, Equatable with `props`.
- Remote data source: an existing `*_remote_data_source.dart` (abstract + `*Imp` using `ApiConsumer`).
- Repository: an existing repository (abstract + `*Imp` returning `FutureResult<T>` — the typedef wrapping the failure/success result — gated on `NetworkStatus`).

## Data layer

- **Naming suffixes**: models → `XModel` in `data/model/` (extend `Equatable`, `fromJson`/`toJson` as needed); params → `XParams` in `data/model/params/` (extend `Equatable`, implement `toJson()`).
- **Data source**: abstract class + `*Imp` implementation using `ApiConsumer`. Pass `params.toJson()` as `body`/`queryParameters`. Parse with `GlobalResponse.fromJson(response.data, fromJsonT: XModel.fromJson)` and return `Future<GlobalResponse<XModel>>`. For untyped responses call `GlobalResponse.fromJson(response.data)` without `fromJsonT`; for payloads not wrapped under a `data` key pass `withDataKey: false`. Do NOT catch — let `Failure` bubble to the repository.
- **Repository**: abstract class + `*Imp` implementation returning `FutureResult<GlobalResponse<T>>`, gated on `NetworkStatus`. Check connectivity first; offline → `Result.failure(ServerFailure.noNetwork())`. Wrap the data-source call in `try`/`on Failure catch (error)` → `Result.failure(error)`; success → `Result.success(result)`. Don't unwrap models here.

```dart
@override
FutureResult<GlobalResponse<XModel>> getX(XParams params) async {
  if (await _network.isConnected) {
    try {
      final result = await _remote.getX(params);
      return Result.success(result);
    } on Failure catch (error) {
      return Result.failure(error);
    }
  }
  return Result.failure(ServerFailure.noNetwork());
}
```

- **Failure type**: the `Failure` hierarchy from `lib/core/error_handling/`.
- **Endpoints**: for any URL that takes a runtime parameter, add a static method on `EndPoints` (in `lib/core/api/api_request_helpers/end_points.dart`) returning the formatted path — `static String getTripById(String tripId) => '$passengers/trips/$tripId';` — and call it as `_apiConsumer.get(EndPoints.getTripById(tripId))`. NEVER interpolate at the call site: `'${EndPoints.trip}/$tripId'` is forbidden. For URLs with no params, keep using `static const String x = '...';`.

## State management (Cubit)

- Use `Cubit` — never `flutter_bloc`'s full `Bloc` / event classes.
- State classes: sealed base class, `final class` variants, Equatable with `props`. The state file is a `part` of the cubit file: `part 'x_state.dart';` in the cubit, `part of 'x_cubit.dart';` in the state.
- **State naming**: every variant must end with the `State` suffix, and states are **per cubit method**: one shared `XInitialState`, then `<Method>LoadingState`, `<Method>SuccessState`, `<Method>FailureState` for each method (e.g. `GetOrdersLoadingState`). Failure states carry the `Failure` payload. The legacy `XInitial` form (no suffix) exists in old files — do NOT copy it.
- **Cubit owns its data lifecycle**: if the cubit has a fetch that should run when the screen opens, call it from the cubit's constructor body — never from a `StatefulWidget.initState`.
- **Cubit stores the data, not the state**: keep the response model in a nullable field on the cubit (`XModel? _xModel;`) so the UI can read it after the success emit — success states stay payload-free.
- **All widget state lives on the cubit**: `TextEditingController`s, `ScrollController`s, form keys, dropdown/picker selections. Dispose disposables in cubit `close()`.

```dart
class XCubit extends Cubit<XState> {
  XCubit(this._repository) : super(const XInitialState()) {
    getX();          // ← initial fetch lives here
  }

  final XRepository _repository;

  XModel? _xModel;
  XModel? get xModel => _xModel;

  Future<void> getX() async {
    emit(const GetXLoadingState());
    final result = await _repository.getX();
    result.when(
      onSuccess: (response) {
        _xModel = response.data;
        emit(const GetXSuccessState());
      },
      onFailure: (failure) => emit(GetXFailureState(failure: failure)),
    );
  }
}
```

## Screens & BlocProvider

- Screens are `StatelessWidget` and contain NO `BlocProvider` — the provider is supplied by the router. The screen consumes the cubit via `context.read<XCubit>()` or `BlocBuilder<XCubit, XState>(...)` directly.
- The only reason to use `StatefulWidget` for a screen is when the widget itself owns a native resource a cubit can't hold (e.g., a `MapController`).

```dart
class XScreen extends StatelessWidget {
  const XScreen({super.key});

  @override
  Widget build(BuildContext context) => Scaffold(
        body: BlocBuilder<XCubit, XState>(builder: ...),
      );
}
```

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

Routes are wired in `lib/core/app_routes/routes_strings.dart` (route constant) and `lib/core/app_routes/app_router.dart` (`case` branch). **The `case` body is where `BlocProvider` lives** — NOT inside the screen widget:

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

## UI conventions

**Widget structure**: NEVER extract widgets as methods (`Widget _buildHeader()`) — ALWAYS create a separate `StatelessWidget` class in its own file. One widget class per file — NEVER put two or more widget classes in the same file. The main screen widget lives in `ui/`; every section/child widget lives in its own file under the sibling `ui/widgets/` dir and gets imported. Name each widget file/class clearly and simply after what it renders (e.g. `order_summary_card.dart` → `OrderSummaryCard`, not `widget1.dart` / `CustomWidget`). Keep UI files under ~150 lines — split into section widgets when they grow. Prefer `StatelessWidget`; use `StatefulWidget` only for pure UI controllers (`AnimationController`, `TabController`). Bottom sheets / dialogs are `StatelessWidget`s that take the cubit as a constructor parameter — the opening screen reads the cubit once, passes it down, and wraps the sheet in `BlocProvider.value(value: cubit, …)`.

**Localization**: every user-facing string (in `AppText`, `PrimaryButton.text`, `GlobalAppbar.titleText`, dialog messages, snackbars, validator messages, etc.) MUST be `LocaleKeys.xxx.tr()` from `easy_localization`. NEVER inline a raw `'...'` literal into a widget shown to the user. If a needed key doesn't exist, invoke the `/add-translation` skill (when available) which adds the key to both `assets/translations/ar.json` and `en.json` in sync — or list the keys (with English wording) and ask the user for the Arabic. Exceptions: debug-only strings (`talker` logs), asset paths, hex colors, route names, regex patterns — anything not shown to the user.

**Widgets — use the core wrappers from `lib/core/widgets/` instead of raw Flutter widgets**:
- `AppText(...)` instead of `Text(...)`
- `AppScaffold(...)` instead of `Scaffold(...)` for screen scaffolds
- `GlobalAppbar(...)` instead of `AppBar(...)` — has `.main` / `.sub` named constructors
- `VerticalSpace(n)` / `HorizontalSpace(n)` instead of `SizedBox(height:/width:)` for spacing; sliver variants `SliverVerticalSpace` / `SliverHorizontalSpace`. Prefer spacing widgets over `Padding` wrappers between `Column`/`Row` children.
- `PrimaryButton(...)` (with `.expand`) and `SecondaryButton(...)` for buttons; `AppTextField(...)` for inputs
- `AppLoader(...)` for loading states; `AppErrorWidget(...)` for failure states
- `AppNetworkImage(...)`, `AppSvgImage(...)`, `AppAssetsImage(...)` for images
- `AppContainer(...)`, `AppDivider(...)`, `AppShimmer(...)`, `AppListTile(...)`, `AppDropDown(...)`, `AppInkWell(...)`, `AppRefreshIndicator(...)`, `AppDialog(...)`, `LabeledContainer(...)`, `HorizontalPadding(...)` as needed
- Also check `animation/` (`AppAnimate`, `TapBounceEffect`) and the root-level widgets (`PaginationWidget`, `CustomCalendar`, `BottomSheetContainer`, …) before writing a new widget.
- Reach for raw Flutter widgets ONLY when no core wrapper covers what you need, and call that gap out.

**Colors — ALWAYS use `AppColors` constants from `lib/core/app_themes/colors/app_colors.dart`. NEVER inline a `Color(0x...)` in presentation code.** If a needed color doesn't exist, add it to `AppColors` first with a descriptive name, then reference the constant.

**Text styles — ALWAYS use `AppTextStyle` (under `lib/core/app_themes/text_style/`). NEVER write raw `TextStyle(fontSize: …, fontWeight: …)` in presentation code.** The class exposes `style<Size><Weight>` getters — weights `Light`, `Regular`, `Medium`, `SemiBold`, `Bold` across sizes 10–32 (e.g. `style12Regular`, `style14Medium`, `style16SemiBold`, `style20Bold`, `style24Bold`, `style28Bold`, `style32Bold`) — check the class for the exact getter before using it; not every size/weight combination exists. For a color, weight tweak, or letterSpacing on top of a base style, use `.copyWith(color: AppColors.X)`. The base styles internally apply `.spMin` for responsive font sizing — clients of `AppTextStyle` do NOT touch `flutter_screenutil` directly.

**Spacing, padding, and sizing — NEVER use `flutter_screenutil` extensions (`.h`, `.w`, `.r`, `.sp`) in presentation code.** Use raw ints / doubles — responsiveness is handled by the design system:
- Gaps: `const VerticalSpace(8)`, `const HorizontalSpace(16)` — NOT `VerticalSpace(8.h)`.
- Padding: `const EdgeInsets.all(16)`, `const EdgeInsets.symmetric(horizontal: 24)` — NOT `EdgeInsets.all(16.r)` or `EdgeInsets.symmetric(horizontal: 24.w)`.
- BorderRadius: `BorderRadius.circular(12)` — NOT `BorderRadius.circular(12.r)`.
- Fixed widths/heights: prefer `AppConstants.X` constants where they exist (e.g. `AppConstants.horizontalPadding` in `lib/core/utils/app_constants.dart`); otherwise raw ints.
- The only place `flutter_screenutil` is allowed is inside `AppTextStyle` and similar core wrappers. Feature code should not even import `package:flutter_screenutil/flutter_screenutil.dart`.

**General style**: single quotes, `const` constructors wherever possible, full 8-digit hex for colors, `final` locals. No `print` — use the `talker` logger. Don't write comments — use self-explanatory names; only comment non-obvious business rules, external constraints, or workarounds.

**Navigation**: `context.pushNamed(...)`, `context.pushReplacementNamed(...)`, `context.pushNamedAndRemoveUntil(name, (_) => false)`, `context.pop()` — never raw `Navigator.of(context)` calls.

## What NOT to do

- Do not introduce `flutter_bloc`'s full `Bloc` / event classes — always `Cubit`.
- Do not add `freezed`, `json_serializable`, or `build_runner` unless they are already in `pubspec.yaml`.
- Do not create model classes the user did not ask for.
- Do not put screens in `StatefulWidget` just to call `context.read<XCubit>().fetch()` in `initState`. The fetch belongs in the cubit constructor.
- Do not wrap the screen widget itself in `BlocProvider`. The provider lives in `app_router.dart`.
- Do not name state variants without the `State` suffix (no `XInitial` — use `XInitialState`), and do not share one generic `XLoadingState` across methods — states are per method (`GetXLoadingState`, `AddXLoadingState`, …).
- Do not carry the fetched data in success states or read it from the state in the UI. Store it in a nullable field on the cubit.
- Do not extract widgets as methods (`Widget _buildHeader()`). Every extracted widget is a `StatelessWidget` class in its own file. Do not put two or more widget classes in the same file, and do not give a widget a vague name (`CustomWidget`, `Widget1`) — name it clearly and simply for what it renders.
- Do not interpolate `EndPoints` constants with runtime params at the call site (no `'${EndPoints.trip}/$tripId'`). Use a static method on `EndPoints`.
- Do not inline new service-locator registrations into `init()`. Put them in a `_<feature>FeatureSetup()` static method and call it from `init()`.
- Do not reach for raw `Text(...)` / `Scaffold(...)` / `SizedBox(height: ...)` / `AppBar(...)` when the corresponding core widget exists. Call out genuine wrapper gaps instead of papering over them.
- Do not inline raw string literals into widgets shown to the user. Every user-facing string is `LocaleKeys.xxx.tr()`.
- Do not write raw `TextStyle(fontSize: …, fontWeight: …, …)` in presentation widgets. Use `AppTextStyle.styleNN<Weight>` (with `.copyWith(...)` for tweaks).
- Do not use `flutter_screenutil` extensions (`.h`, `.w`, `.r`, `.sp`, `.spMin`, `.dm`) in feature presentation code. Spacing/padding/radius take raw ints; fonts go through `AppTextStyle`. (Existing code that did this is legacy; do not copy it.)
- After changes, verify with `flutter analyze` (clean) and run `flutter test` when tests cover the touched code. Do not run the app or any build step.
