---
name: flutter-screen-ui
description: Flutter screen and widget UI conventions — Screen/Body split with BlocListener + AppScaffold, BlocBuilder buildWhen, one widget per file and when to inline, threading cubit data to child widgets, bottom sheets/dialogs, snackbar extension, form validators, localization with LocaleKeys, core widget wrappers (AppText, AppScaffold, GlobalAppbar, VerticalSpace...), AppColors or context.skin, AppTextStyle, spacing without flutter_screenutil, general style, and navigation extensions. Use before writing or editing any Flutter screen, widget, sheet, dialog, or styling code.
---

# Flutter screen & UI

Invoked by the `flutter-knowledge` skill (or directly via `/flutter-screen-ui`) before writing or editing any screen, body, widget, bottom sheet, dialog, or styling code. Related skills: `add-translation` whenever a needed `LocaleKeys` entry is missing, `flutter-cubit` for the cubit the UI reads, `flutter-routing-di` for where the `BlocProvider` lives, `flutter-feature-structure` for where widget files go, and `design-from-html-flutter` when the UI must match an HTML prototype.

**These conventions are the source of truth.** Existing codebases may be old and inconsistent — where legacy code contradicts this skill, follow the skill and do NOT copy the legacy pattern.

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

## UI conventions

**Widget structure**: NEVER extract widgets as methods (`Widget _buildHeader()`) — ALWAYS create a separate `StatelessWidget` class in its own file. One widget class per file — NEVER put two or more widget classes in the same file. The main screen widget lives in `ui/`; every section/child widget lives in its own file under the sibling `ui/widgets/` dir and gets imported. Name each widget file/class clearly and simply after what it renders (e.g. `order_summary_card.dart` → `OrderSummaryCard`, not `widget1.dart` / `CustomWidget`). Keep UI files under ~150 lines — split into section widgets when they grow. Prefer `StatelessWidget`; use `StatefulWidget` only for pure UI controllers (`AnimationController`, `TabController`). Bottom sheets / dialogs are `StatelessWidget`s that take the cubit as a constructor parameter — the opening screen reads the cubit once, passes it down, and wraps the sheet in `BlocProvider.value(value: cubit, …)`.

Splitting into a file is for genuine sections — a form, a card, a list item, anything with its own layout or composition. Don't extract a widget file for a trivial single-line wrapper around one core widget (a lone `AppTextField`, a lone `PrimaryButton` with nothing but an `onPressed`) — write it inline as a widget expression in the parent instead; a dedicated file for it is ceremony without payoff. The line is composition: if a "widget" is just one core-wrapper call with static args, inline it; extract it once it has its own logic, layout, or is reused elsewhere.

**Threading data to child widgets**: only two kinds of widgets take data via constructor parameters — the `<Screen>Body` (via `BlocBuilder`) and true leaf/item widgets (e.g. a list row). Intermediate structural widgets (a list wrapper, a section container) should read the cubit directly via `context.read<XCubit>()` rather than having its data threaded through as a constructor argument one layer at a time. Keep the cubit reference itself, and read its fields off that reference at each use site — `final cubit = context.read<XCubit>(); ...cubit.items.length... cubit.items[index]...` — rather than extracting a field into a separately-defaulted local (`final items = cubit.items ?? const [];`); the local copy can drift from the live cubit field and adds a redundant fallback. Leaf/item widget constructors take plain primitive values (`String id, String status, DateTime date, ...`), never the whole model object — passing the model directly couples the widget to that specific type and makes it unusable anywhere else; primitives keep it reusable.

**Static-only helper classes** (`EndPoints`, `RoutesStrings`, `AppColors`, `AppConstants`, and similar constants holders) are declared `sealed class X { ... }` — never add a private constructor (`X._()`) to block instantiation; `sealed` already prevents it.

**Snackbars**: show them through the `BuildContext` extension (`context.showSnackBar(message)`, typically in `core/utils/extensions.dart`) — never call `ScaffoldMessenger.of(context).showSnackBar(...)` directly in feature code. Mirror whatever extension name the project already uses if it differs.

**Form validation**: check for an existing shared validators helper (e.g. `AppFormValidations` in `lib/core/helpers/validations/`) before writing a field's `validator:`. If one exists, use its static validators (email, phone, password, username, ...) instead of an inline validation closure — this keeps validation rules (and their `LocaleKeys` messages) consistent across every form in the app. Only write an inline validator when the field doesn't match any case the shared helper already covers.

**Localization**: every user-facing string (in `AppText`, `PrimaryButton.text`, `GlobalAppbar.titleText`, dialog messages, snackbars, validator messages, etc.) MUST be `LocaleKeys.xxx.tr()` from `easy_localization`. NEVER inline a raw `'...'` literal into a widget shown to the user. If a needed key doesn't exist, invoke the `add-translation` skill (via the Skill tool, or tell the user to run `/add-translation`) which adds the key to both `assets/translations/ar.json` and `en.json` in sync, writing the English and the Arabic itself. Exceptions: debug-only strings (`talker` logs), asset paths, hex colors, route names, regex patterns — anything not shown to the user.

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
- **Fallback when a wrapper is missing**: before using a wrapper, check that it exists in the project's `lib/core/widgets/`. If the project has no wrapper for what you need (or has no `lib/core/widgets/` at all), use the raw Flutter widget (`Text`, `Scaffold`, `AppBar`, `SizedBox`, ...). Do not import a wrapper that is not in the project, and do not create a new wrapper unless the user asks for one.

**Colors — ALWAYS use `AppColors` constants from `lib/core/app_themes/colors/app_colors.dart`. NEVER inline a `Color(0x...)` in presentation code.** If a needed color doesn't exist, add it to `AppColors` first with a descriptive name, then reference the constant. **Exception:** if the project has `lib/core/app_themes/colors/app_skin.dart`, it has no `AppColors` — colors come from `context.skin.<slot>` instead; invoke the `flutter-app-skin` skill before writing any color, and read `AppColors.X` below as `context.skin.x`.

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

- Do not put screens in `StatefulWidget` just to call `context.read<XCubit>().fetch()` in `initState`. The fetch belongs in the cubit constructor.
- Do not wrap the screen widget itself in `BlocProvider`. The provider lives in `app_router.dart`.
- Do not skip the Screen/Body split or put `BlocListener` inside the Body. The `<Screen>` is always a thin `BlocListener` + `Scaffold` shell; the `<Screen>Body` (always named that, never after its content) holds the `BlocBuilder` and the actual layout.
- Do not write a `BlocBuilder` without `buildWhen`. Name the exact state types it should rebuild on — an unscoped one rebuilds on every emit. (`BlocListener` doesn't need a `listenWhen` unless it would otherwise react to states it shouldn't.)
- Do not build a `Scaffold`/`AppScaffold`/`GlobalAppbar` inside the `<Screen>Body` widget. The scaffold and app bar are built once in the `<Screen>` file; the `Body` only returns the content that goes in `body:`. A scaffold inside `Body` rebuilds the app bar on every state emit and duplicates the screen's scaffold.
- Do not extract widgets as methods (`Widget _buildHeader()`). Every extracted widget is a `StatelessWidget` class in its own file, and no two widget classes share a file. Exception: a trivial one-line wrapper around a single core widget (a lone button, a lone text field) doesn't need its own file — inline it in the parent instead. Do not give an extracted widget a vague name (`CustomWidget`, `Widget1`) — name it clearly and simply for what it renders.
- Do not pass a whole model object into a leaf/item widget's constructor — pass its primitive fields instead so the widget is reusable elsewhere. Do not thread cubit data through intermediate structural widgets via constructor params either — read it directly with `context.read<XCubit>()`, and read fields off that same cubit reference rather than copying one into a separately-defaulted local variable.
- Do not call `ScaffoldMessenger.of(context).showSnackBar(...)` directly in feature code. Use the project's `BuildContext` snackbar extension.
- Do not write an inline validator closure for a field that a shared validators helper (e.g. `AppFormValidations`) already covers — use the shared one.
- Do not add a private constructor (`X._()`) to a static-only constants class (`EndPoints`, `RoutesStrings`, `AppColors`, ...) to block instantiation — declare it `sealed class X` instead.
- Do not reach for raw `Text(...)` / `Scaffold(...)` / `SizedBox(height: ...)` / `AppBar(...)` when the corresponding core widget exists in `lib/core/widgets/`. When it does not exist, fall back to the raw widget instead of importing or inventing a wrapper.
- Do not inline raw string literals into widgets shown to the user. Every user-facing string is `LocaleKeys.xxx.tr()`.
- Do not write raw `TextStyle(fontSize: …, fontWeight: …, …)` in presentation widgets. Use `AppTextStyle.styleNN<Weight>` (with `.copyWith(...)` for tweaks).
- Do not use `flutter_screenutil` extensions (`.h`, `.w`, `.r`, `.sp`, `.spMin`, `.dm`) in feature presentation code. Spacing/padding/radius take raw ints; fonts go through `AppTextStyle`. (Existing code that did this is legacy; do not copy it.)
- Do not transcribe a design from an HTML prototype by eye, and do not set skin/text-style/motion tokens from a screenshot — invoke the `design-from-html-flutter` skill first and extract the values from the prototype's computed CSS.
