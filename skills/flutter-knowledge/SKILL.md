---
name: flutter-knowledge
description: Use anytime Flutter or Dart is mentioned, or for any task touching a Flutter project — writing, editing, reviewing, debugging, explaining, or scaffolding screens, widgets, cubits, blocs, state classes, models, data sources, repositories, routing, dependency injection, styling, theming, or localization in a .dart file or pubspec.yaml.
---

# Flutter knowledge

Full-stack Flutter conventions: architecture, data layer, state management, DI, routing, and UI rules.

**These conventions are the source of truth.** Existing codebases may be old and inconsistent — where legacy code contradicts this skill, follow the skill and do NOT copy the legacy pattern.

## Feature architecture

Features live under `lib/feature/<feature>/` (snake_case — singular `feature`, NOT `features`). Every feature follows this tree — the presentation screen directory MUST be suffixed `_screen`:

```
data/
  data_source/<feature>_remote_data_source.dart
  data_source/<feature>_local_data_source.dart   # only for local-only / hybrid features
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

Omit `data/` entirely for UI-only features. A local-only or hybrid feature also needs local persistence — invoke the matching local-database skill for that (see "Local database" below) before writing any local data source or storage code: `drift-local-database` if the project uses drift, `hive-local-database` if it uses Hive.

Before writing each file, read the equivalent file from an existing feature in the current codebase and mirror its style and import order. Do not invent a different shape:
- Cubit: pick an existing `*_cubit.dart` — note it kicks off the initial fetch from inside the constructor body, NOT from the screen's lifecycle.
- State: pick an existing `*_state.dart` — sealed class, `final class` variants, Equatable with `props`.
- Remote data source: an existing `*_remote_data_source.dart` (abstract + `*Imp` using `ApiConsumer`).
- Repository: an existing repository (abstract + `*Imp` returning `FutureResult<T>` — the typedef wrapping the failure/success result — gated on `NetworkStatus`).

## Data layer

- **Naming suffixes**: models → `XModel` in `data/model/` (extend `Equatable`, `fromJson`/`toJson` as needed); params → `XParams` in `data/model/params/` (extend `Equatable`, implement `toJson()`). **Model fields are always nullable** (`String? name`, `int? total`, ...) — API responses can omit or null out any field, so never declare a model field as required/non-null.
- **One params class per method**: every data source / repository method that takes parameters gets its own dedicated `XParams` class — never share one params class across two methods, even if their fields happen to overlap. If two methods need overlapping fields, that's two separate params classes with duplicated fields, not one shared class.
- **Model member order**: fields first, then the constructor, then `fromJson`, then `toJson` (`props` last, for the `Equatable` override). Keep this order in every model file so they all read the same way.
- **Data source**: abstract class + `*Imp` implementation using `ApiConsumer`. Pass `params.toJson()` as `body`/`queryParameters`. Parse with `GlobalResponse.fromJson(response.data, fromJsonT: XModel.fromJson)` and return `Future<GlobalResponse<XModel>>`. For untyped responses call `GlobalResponse.fromJson(response.data)` without `fromJsonT`; for payloads not wrapped under a `data` key pass `withDataKey: false`. Do NOT catch — let `Failure` bubble to the repository.
- **Repository**: abstract class + `*Imp` implementation returning `FutureResult<GlobalResponse<T>>`, gated on `NetworkStatus`. Check connectivity first; offline → `Result.failure(ServerFailure.noNetwork())`. Wrap the data-source call in `try`/`on Failure catch (error)` → `Result.failure(error)`; success → `Result.success(result)`. Don't unwrap models here.

```dart
@override
FutureResult<GlobalResponse<XModel>> getX(XParams params) async {
  if (await _network.isConnected) {
    try {
      final result = await _remoteDataSource.getX(params);
      return Result.success(result);
    } on Failure catch (error) {
      return Result.failure(error);
    }
  }
  return Result.failure(ServerFailure.noNetwork());
}
```

- **Failure type**: the `Failure` hierarchy from `lib/core/error_handling/`.
- **Endpoints**: for any URL that takes a runtime parameter, add a static method on `EndPoints` (in `lib/core/api/api_request_helpers/end_points.dart`) returning the formatted path — `static String getTripById(String tripId) => '$passengers/trips/$tripId';` — and call it as `_apiConsumer.get(EndPoints.getTripById(tripId))`. NEVER interpolate at the call site: `'${EndPoints.trip}/$tripId'` is forbidden. For URLs with no params, keep using `static const String x = '...';`. `EndPoints` is a `sealed class` holding only static members — do NOT add a private constructor (`EndPoints._()`) to block instantiation; `sealed` already does that.

## Local database

When a feature needs local persistence — offline storage, caching a remote response locally, or a local-only (no API) feature — invoke the local-database skill that matches the project's storage engine before writing any local data source or storage code. Check `pubspec.yaml`:

- **drift** in the project → invoke `drift-local-database` (via the Skill tool, or `/drift-local-database`). It holds the DAO → LocalDataSource → Repository layering, `Entity`/`Companion` naming, migrations, and the local-only/hybrid repository patterns.
- **hive / hive_ce** in the project → invoke `hive-local-database` (via the Skill tool, or `/hive-local-database`). It holds the Box → LocalDataSource → Repository layering, storage↔model mapping, and the local-only/hybrid repository patterns.

If neither is present yet, pick the one the feature calls for (or ask the user) and follow that skill. Either way, do not invent the persistence layer from memory — each is a distinct, validated set of conventions, not something to reconstruct from the general Data layer rules above.

## State management (Cubit)

- Use `Cubit` — never `flutter_bloc`'s full `Bloc` / event classes.
- State classes: sealed base class, `final class` variants, Equatable with `props`. The state file is a `part` of the cubit file: `part 'x_state.dart';` in the cubit, `part of 'x_cubit.dart';` in the state.
- **State naming**: every variant must end with the `State` suffix, and states are **per cubit method**: one shared `XInitialState`, then `<Method>LoadingState`, `<Method>SuccessState`, `<Method>FailureState` for each method (e.g. `GetOrdersLoadingState`). Failure states carry the `Failure` payload. The legacy `XInitial` form (no suffix) exists in old files — do NOT copy it.
- **Cubit owns its data lifecycle**: if the cubit has a fetch that should run when the screen opens, call it from the cubit's constructor body — never from a `StatefulWidget.initState`.
- **Cubit stores the data, not the state**: keep the response model in a plain nullable field directly on the cubit (`XModel? xModel;`) so the UI can read it after the success emit — success states stay payload-free. Don't wrap it in a private field plus a public getter (`_xModel` + `get xModel`) — that's boilerplate for no benefit here; a direct field is simpler.
- **All widget state lives on the cubit**: `TextEditingController`s, `ScrollController`s, form keys, dropdown/picker selections — declared as direct field initializers (`final nameController = TextEditingController();`), not assigned inside the constructor body. When the cubit receives existing data to edit (e.g. an initial model passed in via `registerFactoryParam`), pre-fill each controller with that value directly — `TextEditingController(text: initialModel.name)` — assigned through the constructor's initializer list; never construct it empty and set `.text` afterwards. Dispose disposables in cubit `close()`.

```dart
class XCubit extends Cubit<XState> {
  XCubit(this._repository) : super(const XInitialState()) {
    getX();          // ← initial fetch lives here
  }

  final XRepository _repository;

  XModel? xModel;

  Future<void> getX() async {
    emit(const GetXLoadingState());
    final result = await _repository.getX();
    result.when(
      onSuccess: (response) {
        xModel = response.data;
        emit(const GetXSuccessState());
      },
      onFailure: (failure) => emit(GetXFailureState(failure: failure)),
    );
  }
}
```

A cubit that edits existing data pre-fills its controllers from the initial model, via the initializer list:

```dart
class EditXCubit extends Cubit<EditXState> {
  EditXCubit(this._repository, XModel initialModel)
      : nameController = TextEditingController(text: initialModel.name),
        super(const EditXInitialState());

  final XRepository _repository;
  final TextEditingController nameController;

  @override
  Future<void> close() {
    nameController.dispose();
    return super.close();
  }
}
```

## Screens & BlocProvider

- Screens are `StatelessWidget` and contain NO `BlocProvider` — the provider is supplied by the router. The only reason to use `StatefulWidget` for a screen is when the widget itself owns a native resource a cubit can't hold (e.g., a `MapController`).
- **The screen file is a thin shell, split from its content.** The `<Screen>` widget's only job is: wrap `BlocListener` (for one-off side effects — snackbars, navigation, dialogs) around an `AppScaffold` whose `body` is a separate `<Screen>Body` widget. All the actual display logic — `BlocBuilder`, layout, child widgets — lives in `<Screen>Body`, in its own file under the sibling `ui/widgets/` dir. This split is consistent across every screen: the body widget is always named `<Screen>Body` (e.g. `EditProfileBody`, `OrderHistoryBody`) — never named after its content (`EditProfileForm`, `OrderHistoryList`, ...).
- `BlocListener` always lives in the `<Screen>` file, wrapping the `AppScaffold` — never inside the `Body` widget, and never omitted just because there's nothing to listen for yet.
- **The `<Screen>` also owns the `AppScaffold`/`GlobalAppbar`** — the `Scaffold` shell, its app bar, and its `body:` slot are all built once in the `<Screen>` file. `<Screen>Body` is only ever the *content* passed into that `body:` slot: it returns bare content (a `Column`, `ListView`, loading/error switch, ...), never its own `Scaffold`/`AppScaffold`/`GlobalAppbar`. Building a second scaffold or app bar inside the `Body` is a real bug, not a style nit — it means the app bar rebuilds on every state emit instead of staying put, and the screen effectively has two scaffolds.
- **Every `BlocBuilder` declares `buildWhen`**, naming exactly the state types that should trigger a rebuild — a bare `BlocBuilder<XCubit, XState>` with no `buildWhen` rebuilds on every emit, including states this widget doesn't care about. `BlocListener` does NOT need a matching `listenWhen` by default — only add one if the listener would otherwise fire for states it shouldn't react to.

```dart
class XScreen extends StatelessWidget {
  const XScreen({super.key});

  @override
  Widget build(BuildContext context) => BlocListener<XCubit, XState>(
        listener: (context, state) {
          if (state is GetXFailureState) {
            context.showSnackBar(state.failure.message);
          }
        },
        child: AppScaffold(
          appBar: GlobalAppbar.main(titleText: LocaleKeys.xTitle.tr()),
          body: const XBody(),
        ),
      );
}
```

```dart
// ui/widgets/x_body.dart
class XBody extends StatelessWidget {
  const XBody({super.key});

  @override
  Widget build(BuildContext context) => BlocBuilder<XCubit, XState>(
        buildWhen: (previous, current) =>
            current is GetXLoadingState ||
            current is GetXSuccessState ||
            current is GetXFailureState,
        builder: (context, state) => ...,   // bare content — no Scaffold/AppScaffold/GlobalAppbar here
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

Routes are wired in `lib/core/app_routes/routes_strings.dart` (route constant) and `lib/core/app_routes/app_router.dart` (`case` branch). `RoutesStrings` is a `sealed class` of static route constants — no private constructor needed (see the general rule on static-only classes in UI conventions). **The `case` body is where `BlocProvider` lives** — NOT inside the screen widget:

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

Splitting into a file is for genuine sections — a form, a card, a list item, anything with its own layout or composition. Don't extract a widget file for a trivial single-line wrapper around one core widget (a lone `AppTextField`, a lone `PrimaryButton` with nothing but an `onPressed`) — write it inline as a widget expression in the parent instead; a dedicated file for it is ceremony without payoff. The line is composition: if a "widget" is just one core-wrapper call with static args, inline it; extract it once it has its own logic, layout, or is reused elsewhere.

**Threading data to child widgets**: only two kinds of widgets take data via constructor parameters — the `<Screen>Body` (via `BlocBuilder`) and true leaf/item widgets (e.g. a list row). Intermediate structural widgets (a list wrapper, a section container) should read the cubit directly via `context.read<XCubit>()` rather than having its data threaded through as a constructor argument one layer at a time. Keep the cubit reference itself, and read its fields off that reference at each use site — `final cubit = context.read<XCubit>(); ...cubit.items.length... cubit.items[index]...` — rather than extracting a field into a separately-defaulted local (`final items = cubit.items ?? const [];`); the local copy can drift from the live cubit field and adds a redundant fallback. Leaf/item widget constructors take plain primitive values (`String id, String status, DateTime date, ...`), never the whole model object — passing the model directly couples the widget to that specific type and makes it unusable anywhere else; primitives keep it reusable.

**Static-only helper classes** (`EndPoints`, `RoutesStrings`, `AppColors`, `AppConstants`, and similar constants holders) are declared `sealed class X { ... }` — never add a private constructor (`X._()`) to block instantiation; `sealed` already prevents it.

**Snackbars**: show them through the `BuildContext` extension (`context.showSnackBar(message)`, typically in `core/utils/extensions.dart`) — never call `ScaffoldMessenger.of(context).showSnackBar(...)` directly in feature code. Mirror whatever extension name the project already uses if it differs.

**Form validation**: check for an existing shared validators helper (e.g. `AppFormValidations` in `lib/core/helpers/validations/`) before writing a field's `validator:`. If one exists, use its static validators (email, phone, password, username, ...) instead of an inline validation closure — this keeps validation rules (and their `LocaleKeys` messages) consistent across every form in the app. Only write an inline validator when the field doesn't match any case the shared helper already covers.

**Localization**: every user-facing string (in `AppText`, `PrimaryButton.text`, `GlobalAppbar.titleText`, dialog messages, snackbars, validator messages, etc.) MUST be `LocaleKeys.xxx.tr()` from `easy_localization`. NEVER inline a raw `'...'` literal into a widget shown to the user. If a needed key doesn't exist, invoke the `add-translation` skill (via the Skill tool, or tell the user to run `/add-translation`) which adds the key to both `assets/translations/ar.json` and `en.json` in sync — or list the keys (with English wording) and ask the user for the Arabic. Exceptions: debug-only strings (`talker` logs), asset paths, hex colors, route names, regex patterns — anything not shown to the user.

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

## Unit tests

Only when the user explicitly asks for tests, invoke the `flutter-testing` skill (via the Skill tool, or tell the user to run `/flutter-testing`) before writing any test file — it holds the full mocktail/bloc_test conventions, test layout, and coverage expectations. Do not generate test files as a side effect of scaffolding a feature, and do not invent test structure from memory.

## What NOT to do

- Do not introduce `flutter_bloc`'s full `Bloc` / event classes — always `Cubit`.
- Do not add `freezed`, `json_serializable`, or `build_runner` unless they are already in `pubspec.yaml`.
- Do not implement local persistence (drift/SQLite tables + DAOs, or Hive boxes, offline caching, local-only or hybrid repositories) without invoking the matching local-database skill first — `drift-local-database` for drift, `hive-local-database` for Hive. Do not invent that layer from memory.
- Do not create model classes the user did not ask for.
- Do not reuse one params class across two data source/repository methods, and do not have a parameterized method share another method's params class. Every method gets its own `XParams`, even when the fields would overlap.
- Do not declare model fields as non-nullable. Assume any API field can be missing or null.
- Do not mix up model member order. Fields, then constructor, then `fromJson`, then `toJson` — every model file in the same order.
- Do not put screens in `StatefulWidget` just to call `context.read<XCubit>().fetch()` in `initState`. The fetch belongs in the cubit constructor.
- Do not wrap the screen widget itself in `BlocProvider`. The provider lives in `app_router.dart`.
- Do not skip the Screen/Body split or put `BlocListener` inside the Body. The `<Screen>` is always a thin `BlocListener` + `Scaffold` shell; the `<Screen>Body` (always named that, never after its content) holds the `BlocBuilder` and the actual layout.
- Do not name state variants without the `State` suffix (no `XInitial` — use `XInitialState`), and do not share one generic `XLoadingState` across methods — states are per method (`GetXLoadingState`, `AddXLoadingState`, …).
- Do not carry the fetched data in success states or read it from the state in the UI. Store it in a plain nullable field directly on the cubit — not a private field plus a public getter.
- Do not create a `TextEditingController` empty and fill it with `.text = ...` later when the cubit already has the initial value at construction time — pre-fill it in the constructor's initializer list instead.
- Do not write a `BlocBuilder` without `buildWhen`. Name the exact state types it should rebuild on — an unscoped one rebuilds on every emit. (`BlocListener` doesn't need a `listenWhen` unless it would otherwise react to states it shouldn't.)
- Do not build a `Scaffold`/`AppScaffold`/`GlobalAppbar` inside the `<Screen>Body` widget. The scaffold and app bar are built once in the `<Screen>` file; the `Body` only returns the content that goes in `body:`. A scaffold inside `Body` rebuilds the app bar on every state emit and duplicates the screen's scaffold.
- Do not extract widgets as methods (`Widget _buildHeader()`). Every extracted widget is a `StatelessWidget` class in its own file, and no two widget classes share a file. Exception: a trivial one-line wrapper around a single core widget (a lone button, a lone text field) doesn't need its own file — inline it in the parent instead. Do not give an extracted widget a vague name (`CustomWidget`, `Widget1`) — name it clearly and simply for what it renders.
- Do not pass a whole model object into a leaf/item widget's constructor — pass its primitive fields instead so the widget is reusable elsewhere. Do not thread cubit data through intermediate structural widgets via constructor params either — read it directly with `context.read<XCubit>()`, and read fields off that same cubit reference rather than copying one into a separately-defaulted local variable.
- Do not call `ScaffoldMessenger.of(context).showSnackBar(...)` directly in feature code. Use the project's `BuildContext` snackbar extension.
- Do not write an inline validator closure for a field that a shared validators helper (e.g. `AppFormValidations`) already covers — use the shared one.
- Do not interpolate `EndPoints` constants with runtime params at the call site (no `'${EndPoints.trip}/$tripId'`). Use a static method on `EndPoints`.
- Do not add a private constructor (`X._()`) to a static-only constants class (`EndPoints`, `RoutesStrings`, `AppColors`, ...) to block instantiation — declare it `sealed class X` instead.
- Do not inline new service-locator registrations into `init()`. Put them in a `_<feature>FeatureSetup()` static method and call it from `init()`.
- Do not reach for raw `Text(...)` / `Scaffold(...)` / `SizedBox(height: ...)` / `AppBar(...)` when the corresponding core widget exists. Call out genuine wrapper gaps instead of papering over them.
- Do not inline raw string literals into widgets shown to the user. Every user-facing string is `LocaleKeys.xxx.tr()`.
- Do not write raw `TextStyle(fontSize: …, fontWeight: …, …)` in presentation widgets. Use `AppTextStyle.styleNN<Weight>` (with `.copyWith(...)` for tweaks).
- Do not use `flutter_screenutil` extensions (`.h`, `.w`, `.r`, `.sp`, `.spMin`, `.dm`) in feature presentation code. Spacing/padding/radius take raw ints; fonts go through `AppTextStyle`. (Existing code that did this is legacy; do not copy it.)
- Do not write unit tests unprompted, and do not invent test structure from memory — invoke the `flutter-testing` skill first when the user does ask for tests.
- After changes, verify with `flutter analyze` (clean) and run `flutter test` when tests cover the touched code. Do not run the app or any build step.
