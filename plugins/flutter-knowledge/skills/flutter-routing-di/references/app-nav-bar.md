# App nav bar recipe

Use this recipe every time an app needs a bottom navigation bar, tab shell or main screen with tabs. Build it from scratch with exactly these files, names, states and wiring. Only the look of `AppBottomNavBar` and `AppNavBarItem` follows the design; their APIs, the cubit, the state, the body and the router stay as shown. Do not use `BottomNavigationBar`/`NavigationBar` state, a `StatefulWidget`, a `PageView`, a nested `Navigator` or a router shell route for tab switching.

Invoke `flutter-feature-structure`, `flutter-state-management`, `flutter-screen-ui` and `flutter-routing-di` before writing it, as for any feature. Imports below use the project's import style; `<app>` is the package name. The tabs `home`, `search`, `profile` are placeholders for the app's tabs, in the same order everywhere.

## Files

```
lib/feature/app_nav_bar/
  app_nav_bar_injection.dart
  presentation/app_nav_bar_screen/
    logic/
      app_nav_bar_cubit.dart
      app_nav_bar_state.dart
      helpers/app_nav_tab.dart
    ui/
      app_nav_bar_screen.dart
      widgets/
        app_nav_bar_body.dart
        app_bottom_nav_bar.dart
        app_nav_bar_item.dart
```

No `data/`: the nav bar is UI-only. Each tab is its own feature with its own `<tab>_screen`; the nav bar only hosts those screens.

## Logic

`logic/helpers/app_nav_tab.dart` — one enum value per tab, in display order. Its order is the `IndexedStack` order. Labels use the `appNavBar` group in a grouped translation file; in a flat one they are flat keys (`LocaleKeys.home`), reusing an existing key when the label already exists (`LocaleKeys.trips`).

```dart
import 'package:<app>/core/helpers/app_assets.dart';
import 'package:<app>/core/l10n/locale_keys.g.dart';

enum AppNavTab {
  home(iconPath: AppAssets.homeIcon, labelKey: LocaleKeys.appNavBar_home),
  search(iconPath: AppAssets.searchIcon, labelKey: LocaleKeys.appNavBar_search),
  profile(iconPath: AppAssets.profileIcon, labelKey: LocaleKeys.appNavBar_profile);

  const AppNavTab({required this.iconPath, required this.labelKey});

  final String iconPath;
  final String labelKey;
}
```

`logic/app_nav_bar_cubit.dart` — no constructor dependencies, no fetch. The current tab lives on the cubit.

```dart
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:<app>/feature/app_nav_bar/presentation/app_nav_bar_screen/logic/helpers/app_nav_tab.dart';

part 'app_nav_bar_state.dart';

class AppNavBarCubit extends Cubit<AppNavBarState> {
  AppNavBarCubit() : super(const AppNavBarInitialState());

  AppNavTab currentTab = AppNavTab.home;

  void changeTab(AppNavTab tab) {
    if (tab == currentTab) return;
    currentTab = tab;
    emit(ChangeTabSuccessState(tab));
  }
}
```

`logic/app_nav_bar_state.dart` — `ChangeTabSuccessState` carries the tab only so that two different tab changes are not equal states; the UI still reads `cubit.currentTab`. This is the one sanctioned payload on a success state.

```dart
part of 'app_nav_bar_cubit.dart';

sealed class AppNavBarState extends Equatable {
  const AppNavBarState();

  @override
  List<Object?> get props => [];
}

final class AppNavBarInitialState extends AppNavBarState {
  const AppNavBarInitialState();
}

final class ChangeTabSuccessState extends AppNavBarState {
  const ChangeTabSuccessState(this.tab);

  final AppNavTab tab;

  @override
  List<Object?> get props => [tab];
}
```

## UI

`ui/app_nav_bar_screen.dart` — the thin shell: `AppScaffold` with the body and the bar. If the project's `AppScaffold` has no `bottomNavigationBar` parameter, add it as an optional parameter passed to `Scaffold`; do not use a raw `Scaffold` here.

```dart
import 'package:flutter/material.dart';
import 'package:<app>/core/widgets/layout/app_scaffold.dart';
import 'package:<app>/feature/app_nav_bar/presentation/app_nav_bar_screen/ui/widgets/app_bottom_nav_bar.dart';
import 'package:<app>/feature/app_nav_bar/presentation/app_nav_bar_screen/ui/widgets/app_nav_bar_body.dart';

class AppNavBarScreen extends StatelessWidget {
  const AppNavBarScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return const AppScaffold(
      body: AppNavBarBody(),
      bottomNavigationBar: AppBottomNavBar(),
    );
  }
}
```

`ui/widgets/app_nav_bar_body.dart` — an `IndexedStack` of the tab screens, in `AppNavTab` order, so every tab keeps its state and scroll position. Tab screens are the features' own `<Tab>Screen` widgets, unchanged.

```dart
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:<app>/feature/app_nav_bar/presentation/app_nav_bar_screen/logic/app_nav_bar_cubit.dart';
import 'package:<app>/feature/home/presentation/home_screen/ui/home_screen.dart';
import 'package:<app>/feature/profile/presentation/profile_screen/ui/profile_screen.dart';
import 'package:<app>/feature/search/presentation/search_screen/ui/search_screen.dart';

class AppNavBarBody extends StatelessWidget {
  const AppNavBarBody({super.key});

  @override
  Widget build(BuildContext context) {
    return BlocBuilder<AppNavBarCubit, AppNavBarState>(
      buildWhen: (previous, current) => current is ChangeTabSuccessState,
      builder: (context, state) => IndexedStack(
        index: context.read<AppNavBarCubit>().currentTab.index,
        children: const [
          HomeScreen(),
          SearchScreen(),
          ProfileScreen(),
        ],
      ),
    );
  }
}
```

`ui/widgets/app_bottom_nav_bar.dart` — the bar container. Keep the `SafeArea(top: false)`, the `BlocBuilder` with this `buildWhen`, and one `Expanded` `AppNavBarItem` per `AppNavTab.values`. Its background, border, height and padding come from the design through `context.tokens`.

```dart
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:<app>/core/theme/app_tokens.dart';
import 'package:<app>/feature/app_nav_bar/presentation/app_nav_bar_screen/logic/app_nav_bar_cubit.dart';
import 'package:<app>/feature/app_nav_bar/presentation/app_nav_bar_screen/logic/helpers/app_nav_tab.dart';
import 'package:<app>/feature/app_nav_bar/presentation/app_nav_bar_screen/ui/widgets/app_nav_bar_item.dart';

class AppBottomNavBar extends StatelessWidget {
  const AppBottomNavBar({super.key});

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    final cubit = context.read<AppNavBarCubit>();
    return DecoratedBox(
      decoration: BoxDecoration(
        color: tokens.skin.surface,
        border: Border(top: BorderSide(color: tokens.skin.border)),
      ),
      child: SafeArea(
        top: false,
        child: BlocBuilder<AppNavBarCubit, AppNavBarState>(
          buildWhen: (previous, current) => current is ChangeTabSuccessState,
          builder: (context, state) => Row(
            children: [
              for (final tab in AppNavTab.values)
                Expanded(
                  child: AppNavBarItem(
                    iconPath: tab.iconPath,
                    labelKey: tab.labelKey,
                    isActive: tab == cubit.currentTab,
                    onTap: () => cubit.changeTab(tab),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
```

`ui/widgets/app_nav_bar_item.dart` — the fixed API is `iconPath`, `labelKey`, `isActive`, `onTap`, with `Semantics(button: true, selected: isActive, label: labelKey.tr())` around an `AppInkWell`. Everything inside the `AppInkWell` (indicator, icon size, label style, animation) follows the design through `context.tokens`, `AppSvgImage` and `AppText`.

```dart
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:<app>/core/theme/app_tokens.dart';
import 'package:<app>/core/widgets/buttons/app_ink_well.dart';
import 'package:<app>/core/widgets/images/app_svg_image.dart';
import 'package:<app>/core/widgets/layout/space_widgets.dart';
import 'package:<app>/core/widgets/text/app_text.dart';

class AppNavBarItem extends StatelessWidget {
  const AppNavBarItem({
    super.key,
    required this.iconPath,
    required this.labelKey,
    required this.isActive,
    required this.onTap,
  });

  final String iconPath;
  final String labelKey;
  final bool isActive;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    final color = isActive ? tokens.skin.primary : tokens.skin.textMuted;
    return Semantics(
      button: true,
      selected: isActive,
      label: labelKey.tr(),
      child: AppInkWell(
        onTap: onTap,
        child: Padding(
          padding: EdgeInsets.symmetric(vertical: tokens.space.sm),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              AppSvgImage(path: iconPath, color: color),
              VerticalSpace(tokens.space.xs),
              AppText(labelKey.tr(), style: tokens.text.labelSm.copyWith(color: color)),
            ],
          ),
        ),
      ),
    );
  }
}
```

Mirror the project's real core widget paths, constructor names and token names; the shapes above are fixed, the paths are examples.

## Wiring

`app_nav_bar_injection.dart` registers only the nav bar cubit; each tab's cubit stays in its own feature's injection file. Add `registerAppNavBarDependencies();` to `registerAppDependencies` and `AppNavBarCubit` to `test/app_injection_test.dart`.

```dart
import 'package:<app>/core/di/injection.dart';
import 'package:<app>/feature/app_nav_bar/presentation/app_nav_bar_screen/logic/app_nav_bar_cubit.dart';

void registerAppNavBarDependencies() {
  sl.registerFactory<AppNavBarCubit>(() => AppNavBarCubit());
}
```

`RoutesStrings` gets `static const String appNavBarScreen = '/app-nav-bar-screen';` (mirror the existing route-string format). The route `case` in `lib/core/router/app_router.dart` is the only place the nav bar's and every tab's cubits are provided: one `MultiBlocProvider` on top of `AppNavBarScreen`, with `AppNavBarCubit` first, then one `BlocProvider` per tab screen's cubit in `AppNavTab` order.

```dart
case RoutesStrings.appNavBarScreen:
  return MaterialPageRoute(
    builder: (context) {
      return MultiBlocProvider(
        providers: [
          BlocProvider(create: (context) => sl<AppNavBarCubit>()),
          BlocProvider(create: (context) => sl<HomeCubit>()),
          BlocProvider(create: (context) => sl<SearchCubit>()),
          BlocProvider(create: (context) => sl<ProfileCubit>()),
        ],
        child: const AppNavBarScreen(),
      );
    },
  );
```

The app's post-auth entry (`AppRouter.initialRoute` or the existing login/onboarding success navigation) goes to `RoutesStrings.appNavBarScreen`. A tab screen has no route `case` of its own unless it is also pushed on its own elsewhere; screens pushed from a tab (details, edit) get their own route and `BlocProvider` as usual.

## Adding or removing a tab

Change all four places together, in the same order: the `AppNavTab` value, the `IndexedStack` child in `AppNavBarBody`, the tab cubit's `BlocProvider` in the route's `MultiBlocProvider`, and the `appNavBar` localization key in both translation files.

## What NOT to do

- Do not keep the selected index in a widget, a `StatefulWidget`, a `ValueNotifier` or the state; it is `AppNavBarCubit.currentTab`.
- Do not wrap `AppNavBarScreen`, `AppNavBarBody` or a tab screen in `BlocProvider`; all of them are provided by the route's `MultiBlocProvider`.
- Do not register a tab cubit in `app_nav_bar_injection.dart`, or `AppNavBarCubit` as a singleton.
- Do not build tabs with `PageView`, `TabBarView`, nested `Navigator`s or a `switch` that recreates the screen on each tab change; use the `IndexedStack`.
- Do not add a tab screen's own `AppScaffold` app bar to `AppNavBarScreen`; each tab screen keeps its own `AppScaffold`/`GlobalAppbar`.
