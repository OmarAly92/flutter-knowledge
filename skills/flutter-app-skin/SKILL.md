---
name: flutter-app-skin
description: AppSkin color and theme conventions for a Flutter project whose colors live in an abstract AppSkin with LightSkin/DarkSkin (lib/core/app_themes/colors/app_skin.dart) — reading colors with context.skin, adding a color slot, light/dark switching with SkinCubit, SkinScope wiring, and building ThemeData with AppThemes.fromSkin. Use before writing any color, adding a skin slot, touching dark mode or the theme, or editing app_skin.dart, light_skin.dart, dark_skin.dart or app_themes.dart.
---

# App skin (colors and light/dark themes)

Invoked by the `flutter-knowledge` skill (or directly via `/flutter-app-skin`) whenever a project keeps its colors in an `AppSkin`. Check first: the project uses a skin if `lib/core/app_themes/colors/app_skin.dart` exists or `grep -rn "class AppSkin" lib` finds one. Then this skill replaces the `AppColors` rule in `flutter-screen-ui`: every color is `context.skin.<slot>`, and `AppColors` is never used or created. If the project only has a flat `AppColors` class, keep using `AppColors` and do not migrate it to a skin unless the user asks — and no partial migration on the side either (no `SkinCubit` or `SkinScope`, no few widgets switched to `context.skin`). A project that has both is mid-migration: new code uses `context.skin`, and existing `AppColors` references stay until the user asks for that file to be migrated.

**Follow the project first.** Read the project's `app_skin.dart`, both skins, `skin_scope.dart` and `logic/skin_cubit.dart` before adding anything, and mirror what is there (slot names, which cubit methods exist). If `lib/core/app_themes/colors/README.md` exists, read it before touching the skin or the theme — it is that project's own reference. The shape below is the default when you are building the skin layer from scratch, and the yardstick when the project's version is incomplete.

## The one rule

**Feature code reads colors only through `context.skin.<slot>`.**

- Never a raw `Color(0x…)` or `Colors.x` in presentation code (`Colors.transparent` is the one exception). Reaching for one means a slot is missing: add the slot (see "Adding a color").
- Never `Theme.of(context).colorScheme.…` in the app's own widgets. The `ColorScheme` exists for Material's widgets and third-party packages.
- Never `AppColors` — a skin project has no `AppColors` class, and must not grow one.
- Never pick a color by checking the mode in a widget (`themeMode == ThemeMode.dark ? … : …`). If the two skins need different colors, that difference belongs in the skins: override the slot in `DarkSkin`.

The only place a raw `Color(0x…)` is written is inside `LightSkin`/`DarkSkin` (and, for fixed design constants such as a brand gradient, inside an `AppSkin` default getter).

## The files

```
lib/core/app_themes/
  colors/
    app_skin.dart        # abstract AppSkin — the palette contract
    light_skin.dart      # class LightSkin extends AppSkin
    dark_skin.dart       # class DarkSkin extends AppSkin
    skin_scope.dart      # SkinScope InheritedWidget + `context.skin` extension
    logic/
      skin_cubit.dart    # SkinCubit — holds the active skin, persists it
      skin_state.dart    # part of skin_cubit.dart
  themes/
    app_themes.dart      # sealed class AppThemes { static ThemeData fromSkin(AppSkin skin) }
```

How a color reaches a widget:

```
CacheHelper(CacheKeys.currentTheme)  -- restores 'light' | 'dark' on launch
  -> SkinCubit (field `AppSkin skin`, emits SkinChangedState on change)
  -> MyApp's BlocBuilder<SkinCubit, SkinState> rebuilds
       -> SkinScope(skin: skin)  -> context.skin.<slot>        (the app's own widgets)
       -> MaterialApp(theme: AppThemes.fromSkin(const LightSkin()),
                      darkTheme: AppThemes.fromSkin(const DarkSkin()),
                      themeMode: skin.themeMode) -> Theme.of(context)  (Material widgets, packages)
```

Both consumers rebuild from the same `BlocBuilder`, so they can never disagree about which skin is active.

## Using a color

Import `package:<app>/core/app_themes/colors/skin_scope.dart` and read the slot inside `build`:

```dart
class ChatDayChip extends StatelessWidget {
  const ChatDayChip({super.key, required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
        decoration: BoxDecoration(
          color: context.skin.card,
          borderRadius: BorderRadius.circular(AppConstants.radiusPill),
        ),
        child: AppText(
          label,
          style: AppTextStyle.overline.copyWith(color: context.skin.textMuted),
        ),
      ),
    );
  }
}
```

- Text color goes on an `AppTextStyle` via `.copyWith(color: context.skin.x)` — never a raw `TextStyle`. When the project's `AppText` defaults its color to `context.skin.textPrimary` (check it), pass a color only when the text is not primary.
- When a `build` reads many slots, take `final skin = context.skin;` once at the top of `build` (or of a `BlocBuilder` builder) and use `skin.x`.
- Read `context.skin` in `build` only. Never store the skin in a field, a `static`, `initState`, or a cubit — `context.skin` registers a `SkinScope` dependency, and that dependency is what rebuilds the widget when the user switches skins. Cubits and other non-widget code never touch colors: when logic decides how something looks, it exposes a meaning (an enum or a state field such as `TripStatus.past`), and the widget maps that meaning to a skin slot in `build`.
- Prefer the component slot over the raw palette when one exists: a bottom sheet uses `bottomSheetBackground`, not `surface`; a text field border uses `textFieldBorder`, not `border`; a destructive button uses `dangerButtonBackground`/`dangerButtonText`. Component slots are where a skin overrides a color for one component without touching the rest.
- A core widget that lets callers change a color takes a nullable `Color?` parameter and falls back to its slot: `backgroundColor ?? context.skin.buttonBackground`, `glowColor ?? context.skin.primaryGlow`. Callers pass another slot (`glowColor: context.skin.dangerGlow`), never a literal.
- A package widget that reads `Theme.of(context).colorScheme` itself (sheets, snackbars, loaders, refresh indicators) is used through the project's app wrapper (`showAppSheet`, `context.showSnackBar`, `AppLoader`, `AppRefreshIndicator`, …), which passes the skin's colors in. Do not call the raw package from feature code.
- Shadows are built at the call site from a skin color: `BoxShadow(color: context.skin.primaryGlow, blurRadius: 18, offset: const Offset(0, 6))`. Blur, offsets, radii and other sizes are not skin slots — they go in `AppConstants` or stay at the call site.
- Alpha variants that the design uses repeatedly (glows, translucent bars, focus rings) are slots too (`primaryGlow => primary.withValues(alpha: 0.25)`). A one-off `.withValues(alpha: …)` on a slot at the call site is fine; a repeated one becomes a slot.

## `AppSkin` — the contract

`AppSkin` is an abstract class with a `const AppSkin();` constructor and two kinds of getters:

1. **Abstract slots — the raw palette.** Every skin must implement them: `themeMode`, the page ladder (`background`, `surface`, `card` for sunken blocks, `surfaceElevated`), the borders (`border`, `borderStrong`, `borderSubtle`), the brand set (`primary`, `primaryHover`, `primaryDark`, `primaryLight`), the accent set (`accent`, `accentLight`, `onAccent`), the text set (`textPrimary`, `textSecondary`, `textMuted`, `textOnPrimary`), the status pairs (`success`/`successLight`, `error`/`errorLight`, `warning`/`warningLight`, `info`), and any color that genuinely differs per skin and cannot be derived.
2. **Derived slots — semantic and component colors with a default** computed from the raw palette. A skin overrides one only where the default does not hold for it:

```dart
Color get bottomSheetBackground => surface;
Color get chipBackground => primaryLight;
Color get chipText => primaryDark;
Color get textFieldFocusedBorder => primary;
Color get shadow => textPrimary.withValues(alpha: 0.05);
Color get primaryGlow => primary.withValues(alpha: 0.25);
```

Every slot, abstract or derived, has a `///` doc comment saying what it colors plus `Example:` naming a real place in the app's UI. That comment is what makes "which color goes here?" answerable without the design file — write one for every slot you add.

```dart
/// The fill of small rounded label pills. Example: the soft green fill
/// behind the 'AI' badge on a calendar event.
Color get chipBackground => primaryLight;
```

**Slots are colors.** A slot returns a `Color` (occasionally a `Gradient` for a fixed design gradient). Do not put `double` sizes, `List<BoxShadow>`, or lists of palette colors on `AppSkin`; keep the per-skin layer to colors so each skin stays a short list of values.

**Naming:**
- A role and its tints: `x` (the color), `xLight` (a soft tint used as a background behind `x` content), `xDark` (a readable shade for text on `xLight`), `xHover` (pressed/hover shade).
- Ink on a fill: `onX` (`onAccent`, `onInverseSurface`), and `textOnPrimary` for text on `primary`.
- Component slots: `<component><Part>` — `buttonBackground`, `buttonDisabledText`, `textFieldFocusedBorder`, `navBarItemActive`, `bottomSheetHandle`, `segmentedThumb`.
- Shadow colors end in `Glow` or `Shadow` (`primaryGlow`, `dangerGlow`, `pushLayerShadow`).

## The skins

```dart
class LightSkin extends AppSkin {
  const LightSkin();

  @override
  ThemeMode get themeMode => ThemeMode.light;

  @override
  Color get background => const Color(0xFFFAF7F2);

  @override
  Color get surface => const Color(0xFFFFFFFF);

  // ...every abstract slot
}

class DarkSkin extends AppSkin {
  const DarkSkin();

  @override
  ThemeMode get themeMode => ThemeMode.dark;

  @override
  Color get background => const Color(0xFF18171C);

  // ...every abstract slot, then only the derived slots whose default is wrong in dark:

  @override
  Color get bottomSheetBackground => surfaceElevated;
}
```

- Both skins have `const` constructors and are always used as `const LightSkin()` / `const DarkSkin()`.
- Colors are full 8-digit hex `const Color(0xAARRGGBB)`; a translucent design token is written with its alpha baked into the hex (`0x12FFFFFF` for white at 7%).
- Override a derived slot in a skin only where its default does not hold (a sheet must lift off the page in dark mode, so `DarkSkin` maps `bottomSheetBackground` to `surfaceElevated`). Do not re-declare a derived slot with the same value as the default.

## Adding a color

1. **Look for an existing slot first** — read `app_skin.dart`; the right slot often already exists under a component name.
2. **Prefer a derived slot.** If the color can be expressed from the raw palette, add it to `AppSkin` with a default and a doc comment. Both skins inherit it; nothing else changes.
3. **Add an abstract slot only** when the color genuinely differs per skin and cannot be derived. Implement it in `LightSkin` **and** `DarkSkin` (the compiler enforces this).
4. If a Material widget or package should also pick the color up, wire the slot into `AppThemes.fromSkin` too.

## Switching skins

```dart
context.toggleSkin();              // light <-> dark, persisted
context.setSkin(const DarkSkin()); // explicit
```

Both come from the `SkinSwitcherContext` extension in `logic/skin_cubit.dart`. A switch reads the current mode from the skin itself:

```dart
SettingsSwitch(
  value: context.skin.themeMode == ThemeMode.dark,
  onChanged: (_) => context.toggleSkin(),
)
```

Never read or write `CacheKeys.currentTheme` from feature code, and never provide a second `SkinCubit` — the one at the app root is the only one. If the project's cubit has more methods (for example a `setSystemSkin()` that follows the platform brightness), use them; do not add one the user did not ask for. If the user does ask for a "follow the system" mode, save `ThemeMode.system.name`, resolve it in `_savedSkin`, and also listen for OS brightness changes (`WidgetsBindingObserver.didChangePlatformBrightness`) so the skin updates while the app is open — sampling brightness only at launch is a bug.

## Wiring (building the skin layer from scratch)

`skin_scope.dart`:

```dart
class SkinScope extends InheritedWidget {
  const SkinScope({super.key, required this.skin, required super.child});

  final AppSkin skin;

  static AppSkin of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<SkinScope>();
    assert(scope != null, 'SkinScope not found above this context');
    return scope!.skin;
  }

  @override
  bool updateShouldNotify(SkinScope oldWidget) => skin != oldWidget.skin;
}

extension SkinContext on BuildContext {
  AppSkin get skin => SkinScope.of(this);
}
```

`logic/skin_cubit.dart` (state in `skin_state.dart`, `part of 'skin_cubit.dart';`: a `sealed class SkinState extends Equatable` with `SkinInitialState` and `SkinChangedState(this.skin)`, `props => [skin]`):

```dart
class SkinCubit extends Cubit<SkinState> {
  SkinCubit() : skin = _savedSkin(), super(const SkinInitialState());

  AppSkin skin;

  static AppSkin _savedSkin() {
    return CacheHelper.get(CacheKeys.currentTheme) == ThemeMode.dark.name
        ? const DarkSkin()
        : const LightSkin();
  }

  void setSkin(AppSkin newSkin) {
    skin = newSkin;
    CacheHelper.save(CacheKeys.currentTheme, newSkin.themeMode.name);
    emit(SkinChangedState(newSkin));
  }

  void toggleSkin() {
    setSkin(
      skin.themeMode == ThemeMode.dark ? const LightSkin() : const DarkSkin(),
    );
  }
}

extension SkinSwitcherContext on BuildContext {
  void setSkin(AppSkin skin) => read<SkinCubit>().setSkin(skin);

  void toggleSkin() => read<SkinCubit>().toggleSkin();
}
```

`my_app.dart` — `SkinCubit` is provided at the root (not in `app_router.dart`, not in `get_it`), and `SkinScope` sits **above** `MaterialApp` so routes, dialogs and bottom sheets all see it:

```dart
MultiBlocProvider(
  providers: [BlocProvider(create: (context) => SkinCubit())],
  child: BlocBuilder<SkinCubit, SkinState>(
    buildWhen: (previous, current) => current is SkinChangedState,
    builder: (context, state) {
      final skin = context.read<SkinCubit>().skin;
      return SkinScope(
        skin: skin,
        child: MaterialApp(
          theme: AppThemes.fromSkin(const LightSkin()),
          darkTheme: AppThemes.fromSkin(const DarkSkin()),
          themeMode: skin.themeMode,
          // ...
        ),
      );
    },
  ),
)
```

## `AppThemes.fromSkin` — the bridge to Material

`sealed class AppThemes` with one `static ThemeData fromSkin(AppSkin skin)`. Every component theme (`appBarTheme`, `dialogTheme`, `bottomSheetTheme`, `navigationBarTheme`, `switchTheme`, `checkboxTheme`, `timePickerTheme`, …) reads skin slots — the same slots the app's own widgets use (`skin.appBarBackground`, `skin.dialogBackground`, `barrierColor: skin.overlayBarrier`).

For the `ColorScheme`, **map every role explicitly** in `ColorScheme.fromSeed(seedColor: skin.primary, brightness: …, …)`. Any role left out is invented by Material's tonal-palette algorithm from the seed, and Material widgets and packages will draw with a color nobody chose. The usual mapping:

| ColorScheme role | AppSkin slot |
| --- | --- |
| `primary` / `onPrimary` | `primary` / `textOnPrimary` |
| `primaryContainer` / `onPrimaryContainer` | `primaryLight` / `primaryDark` |
| `secondary`, `tertiary` / `onSecondary`, `onTertiary` | `accent` / `onAccent` (one accent hue: both share it) |
| `secondaryContainer`, `tertiaryContainer` / `on…Container` | `accentLight` / `accent` |
| `surface` / `onSurface` / `onSurfaceVariant` | `surface` / `textPrimary` / `textSecondary` |
| `surfaceContainerLowest` → `Highest` | the app's own elevation ladder: `card`, `background`, `surface`, `surfaceElevated`, `surfaceElevated` |
| `inverseSurface` / `onInverseSurface` | `inverseSurface` / `onInverseSurface` |
| `outline` / `outlineVariant` | `border` / `borderSubtle` |
| `error` / `onError` / `errorContainer` / `onErrorContainer` | `error` / `dangerButtonText` / `errorLight` / `error` |

**Do not map `shadow` or `scrim`.** `skin.shadow` and `skin.overlayBarrier` already bake their alpha in for direct use in a `BoxShadow` or a barrier, while Material composites `colorScheme.shadow`/`scrim` itself; mapping them flattens elevation app-wide. The rule: map roles used as-is (surfaces, text, borders, containers); never map a role Material alpha-composites when the slot already carries alpha.

If the project has a test that asserts the `ColorScheme` mapping, update it in the same change as the mapping.

## Adding a new skin

Extend `AppSkin`, implement every abstract slot, override only the derived slots that do not hold, then register it in `SkinCubit` (restore and toggle) and in `MyApp`'s `theme`/`darkTheme`, and add it to any mapping test.

## What NOT to do

- Do not write `Color(0x…)`, `Colors.x` (other than `Colors.transparent`) or `AppColors.x` in feature or core-widget code — add or reuse a slot.
- Do not put sizes, blur values, shadow lists or palettes on `AppSkin` — slots are colors.
- Do not read `Theme.of(context).colorScheme` in the app's own widgets — use `context.skin`, and reach package widgets through the app's wrappers.
- Do not branch on dark/light in a widget to pick a color — override the slot in the skin.
- Do not add a slot without a `///` doc comment naming where it is used.
- Do not add an abstract slot when a derived default would do, and do not implement a new abstract slot in only one skin.
- Do not cache the skin outside `build`, or read colors in a cubit.
- Do not provide `SkinCubit` anywhere but the app root, or touch `CacheKeys.currentTheme` outside `SkinCubit`.
- Do not leave a `ColorScheme` role to `fromSeed`, and do not map `shadow`/`scrim`.
