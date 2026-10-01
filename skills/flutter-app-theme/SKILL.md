---
name: flutter-app-theme
description: Theme conventions for a Flutter app's lib/core/theme layer — the AppTokens ThemeExtension read as context.tokens (skin colors, space, radius, text, elevation, motion, shape), skins as a list (built-in LightSkin/DarkSkin plus JSON skins in a SkinRegistry, chosen with SkinCubit.select and a picker sheet), AppTypography text styles, AppMotion durations/curves/springs/stagger, AppSpacing/AppRadius/AppElevation, AppShapes, and ThemeData built by AppTheme.of(skin) with the ColorScheme mapping. Use before writing any animation, duration or curve; adding a color, spacing, radius, text style, shadow, motion or shape token; adding or switching a skin; touching ThemeData; or editing a file under lib/core/theme/.
---

# App theme (`lib/core/theme`)

Invoked by the `flutter-knowledge` skill (or directly via `/flutter-app-theme`). The theme layer holds every visual value the app shares — colors, spacing, radii, text styles, shadows, motion, shapes — and the `ThemeData` that hands them to Material. **Feature code never invents a visual value — it picks a token. A missing token is added to the theme layer, with a `///` doc comment saying what it is for and `Example:` naming a real place in the UI, and then picked.**

**Follow the project first.** Before adding anything, read the theme files for the part you are touching and mirror them (names, which tokens exist, which helpers exist). If the project documents its theme (`lib/core/theme/README.md`, `lib/core/theme/skin/README.md`, `assets/skins/README.md`, `docs/design/*.md`), read the relevant doc first — it is that project's own reference. The shapes below are the default when you build a part from scratch, and the yardstick when the project's version is incomplete.

**Older project.** The project uses this layer if `lib/core/theme/app_tokens.dart` exists or `grep -rn "class AppTokens" lib` finds one. If not, it predates `context.tokens`: keep its own theme classes and mirror them — colors from `context.skin` (an `AppSkin` with `SkinScope`) or a flat `AppColors`, text from `AppTextStyle`, motion from a static `AppMotion`, radii as raw numbers — and apply the rules below with those names. Do not migrate it, or half-migrate a few widgets, unless the user asks; when they do, build the layer described here.

## The layer

```
lib/core/theme/
  app_tokens.dart          # AppTokens (ThemeExtension) + the `context.tokens` extension
  app_theme.dart           # abstract final class AppTheme — of(skin) / light / dark → ThemeData
  app_spacing.dart         # AppSpacing    → tokens.space
  app_radius.dart          # AppRadius     → tokens.radius
  app_elevation.dart       # AppElevation  → tokens.elevation (built from the skin)
  app_shapes.dart          # AppShapes     → tokens.shape (optional, M3 Expressive polygons)
  typography/
    app_typography.dart    # AppTypography → tokens.text
    app_fonts.dart         # sealed class AppFonts — font family names (static, not a token)
    font_weight_helper.dart  # sealed class FontWeightHelper — named weights (static)
  motion/
    app_motion.dart        # AppMotion     → tokens.motion
    spring_page_physics.dart  # SpringPagePhysics for PageViews (optional)
  skin/
    app_skin.dart          # abstract AppSkin — the palette contract
    light_skin.dart, dark_skin.dart   # the built-in skins
    json_skin.dart         # JsonSkin — a skin read from assets/skins/*.json
    loading/               # SkinSource, the JSON parser, SkinRegistry
    logic/                 # SkinCubit + skin_state.dart
assets/skins/*.json        # extra skins, one file each
```

## The one door: `context.tokens`

Every token is read as **`context.tokens.<group>.<name>`**:

| Group | Class | Holds |
| --- | --- | --- |
| `skin` | `AppSkin` | colors |
| `space` | `AppSpacing` | `xs` 4, `sm` 8, `md` 12, `lg` 16, `xl` 20, `xxl` 24, `xxxl` 32; `screenH` (the screen's horizontal edge `EdgeInsets`) |
| `radius` | `AppRadius` | `BorderRadius` getters `xs … pill` and semantic `card`, `input`, `button`, `sheet`; `…Value` doubles for `Radius.circular` |
| `text` | `AppTypography` | text styles |
| `elevation` | `AppElevation` | `low`, `high`, `glow({Color? color})` — shadow lists colored from the skin |
| `motion` | `AppMotion` | durations, curves, springs, offsets, `staggerAt` / `revealAt` |
| `shape` | `AppShapes` | morphing shape pairs |

`AppTokens` is a `ThemeExtension` registered on `ThemeData.extensions`, so everything under `MaterialApp` — routes, sheets, dialogs, overlays — sees it with no scope widget, and a widget that reads it rebuilds when the skin changes. Only `skin` and `elevation` differ between skins; the other groups are the same `standard` instance for every skin.

```
main(): await sl<SkinRegistry>().load()     built-in + assets/skins/*.json
MyApp → BlocBuilder<SkinCubit, SkinState>
  → ScreenUtilInit                          text sizes use .spMin
    → MaterialApp(theme: AppTheme.of(skin))
      → ThemeData(colorScheme: …mapped from skin…,   Material widgets + packages
                  extensions: [AppTokens.of(skin)])  the app's own widgets
        → context.tokens == Theme.of(context).extension<AppTokens>()
```

Rules for reading tokens:

1. Read them inside `build` (or a method `build` calls), once: `final tokens = context.tokens;`.
2. **Never** read `context.tokens` in `initState`, `dispose`, a `late final` initializer, a constructor or a cubit — `Theme.of` asserts there. In exactly those places use the statics **`AppMotion.standard`** / **`AppShapes.standard`**; everywhere a `BuildContext` is available in `build`, use `context.tokens`.
3. A helper with no `BuildContext` takes the tokens as a parameter (`_style(AppTokens tokens)`), not the statics.
4. Tokens are not `const`. When one lands in a `const` expression, drop the `const`.
5. Never cache `ThemeData`: `AppTheme.light`, `.dark` and `.of(skin)` are getters on purpose, because text sizes depend on `ScreenUtil` and the screen.
6. Never wrap a subtree in `Theme(data: ThemeData(...))` — it drops the `AppTokens` extension.
7. A widget test puts a themed `MaterialApp` above the widget, inside `ScreenUtilInit`; without it `context.tokens` throws:

```dart
await tester.pumpWidget(
  ScreenUtilInit(
    designSize: const Size(375, 812),
    minTextAdapt: true,
    builder: (_, _) => MaterialApp(
      theme: AppTheme.light,
      home: const Scaffold(body: MyWidget()),
    ),
  ),
);
```

## Colors (the skin)

### The one rule

**Feature code reads colors only through `context.tokens.skin.<slot>`.**

- Never a raw `Color(0x…)` or `Colors.x` in presentation code (`Colors.transparent` is the one exception). Reaching for one means a slot is missing: add the slot (see "Adding a color").
- Never `Theme.of(context).colorScheme.…` in the app's own widgets. The `ColorScheme` exists for Material's widgets and third-party packages.
- Never pick a color by checking the mode in a widget (`themeMode == ThemeMode.dark ? … : …`). If skins need different colors, that difference belongs in the skins.

The only place a raw `Color(0x…)` is written is inside a built-in skin (and, for fixed design constants such as a brand gradient, inside an `AppSkin` default getter). JSON skins write hex strings.

```dart
class ChatDayChip extends StatelessWidget {
  const ChatDayChip({super.key, required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    return Center(
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: tokens.space.md, vertical: tokens.space.xs),
        decoration: BoxDecoration(
          color: tokens.skin.card,
          borderRadius: tokens.radius.pill,
        ),
        child: AppText(
          label,
          style: tokens.text.overline.copyWith(color: tokens.skin.textMuted),
        ),
      ),
    );
  }
}
```

- Text color goes on a `tokens.text` style via `.copyWith(color: tokens.skin.x)`. When the project's `AppText` defaults its color to `skin.textPrimary` (check it), pass a color only when the text is not primary.
- Cubits and other non-widget code never touch colors: when logic decides how something looks, it exposes a meaning (an enum or a state field such as `TripStatus.past`), and the widget maps that meaning to a skin slot in `build`.
- Prefer the component slot over the raw palette when one exists: a bottom sheet uses `bottomSheetBackground`, not `surface`; a text field border uses `textFieldBorder`, not `border`; a destructive button uses `dangerButtonBackground`/`dangerButtonText`. Component slots are where a skin overrides a color for one component without touching the rest.
- A core widget that lets callers change a color takes a nullable `Color?` parameter and falls back to its slot: `backgroundColor ?? tokens.skin.buttonBackground`, `glowColor ?? tokens.skin.primaryGlow`. Callers pass another slot (`glowColor: tokens.skin.dangerGlow`), never a literal.
- A package widget that reads `Theme.of(context).colorScheme` itself (sheets, snackbars, loaders, refresh indicators) is used through the project's app wrapper (`showAppSheet`, `context.showSnackBar`, `AppLoader`, `AppRefreshIndicator`, …). Do not call the raw package from feature code.
- Alpha variants that the design uses repeatedly (glows, translucent bars, focus rings) are slots too (`primaryGlow => primary.withValues(alpha: 0.25)`). A one-off `.withValues(alpha: …)` on a slot at the call site is fine; a repeated one becomes a slot.

### `AppSkin` — the contract

`AppSkin` is an abstract class with a `const AppSkin();` constructor, an identity, and two kinds of color getters.

**Identity.** `String get id` (`'light'` / `'dark'` for the built-ins, the file's `id` for a JSON skin — skins are equal by id), `String displayName(Locale locale)` (the name in the picker; built-ins return a `LocaleKeys` string), and `ThemeMode get themeMode` (light or dark — sets `ThemeData.brightness`, so the status bar, keyboard and Material widgets follow).

1. **Base slots — the raw palette.** Abstract; every skin supplies them: the page ladder (`background`, `surface`, `card` for sunken blocks, `surfaceElevated`), the borders (`border`, `borderStrong`, `borderSubtle`), the brand set (`primary`, `primaryHover`, `primaryDark`, `primaryLight`), the accent set (`accent`, `accentLight`, `onAccent`), the text set (`textPrimary`, `textSecondary`, `textMuted`, `textOnPrimary`), the status pairs (`success`/`successLight`, `error`/`errorLight`, `warning`/`warningLight`, `info`), and any color that genuinely differs per skin and cannot be derived. Their names are listed in `static const baseSlotNames`.
2. **Derived slots — semantic and component colors with a default** computed from the base palette. A skin overrides one only where the default does not hold for it. Their names are listed in `static const derivedSlotNames`.

```dart
/// The fill of small rounded label pills. Example: the soft green fill
/// behind the 'AI' badge on a calendar event.
Color get chipBackground => primaryLight;

Color get bottomSheetBackground => surface;
Color get shadow => textPrimary.withValues(alpha: 0.05);
Color get primaryGlow => primary.withValues(alpha: 0.25);
```

Every slot has a `///` doc comment saying what it colors plus `Example:` naming a real place in the app's UI — that is what makes "which color goes here?" answerable without the design file. Derived defaults are tuned for a light palette; a dark skin overrides the ones that do not hold.

**Slots are colors.** A slot returns a `Color` (occasionally a `Gradient` for a fixed design gradient). Sizes, blur values and shadow lists live in `AppSpacing`/`AppRadius`/`AppElevation`, not on `AppSkin`.

**Naming:**
- A role and its tints: `x` (the color), `xLight` (a soft tint used as a background behind `x` content), `xDark` (a readable shade for text on `xLight`), `xHover` (pressed/hover shade).
- Ink on a fill: `onX` (`onAccent`, `onInverseSurface`), and `textOnPrimary` for text on `primary`.
- Component slots: `<component><Part>` — `buttonBackground`, `buttonDisabledText`, `textFieldFocusedBorder`, `navBarItemActive`, `bottomSheetHandle`, `segmentedThumb`.
- Shadow colors end in `Glow` or `Shadow` (`primaryGlow`, `dangerGlow`, `pushLayerShadow`).

### The skins

There are three kinds: the built-in `LightSkin` and `DarkSkin` (Dart), and `JsonSkin`, built from an `assets/skins/*.json` file (base slots from the file's `colors`, each derived slot from its `overrides` or else the formula).

```dart
class LightSkin extends AppSkin {
  const LightSkin();

  @override
  String get id => 'light';

  @override
  String displayName(Locale locale) => LocaleKeys.themeLight.tr();

  @override
  ThemeMode get themeMode => ThemeMode.light;

  @override
  Color get background => const Color(0xFFFAF7F2);

  // ...every base slot; DarkSkin also overrides the derived slots whose
  // default is wrong in dark (e.g. bottomSheetBackground => surfaceElevated)
}
```

- Built-in skins have `const` constructors and are always used as `const LightSkin()` / `const DarkSkin()`. `LightSkin` is the ultimate fallback.
- Colors are full 8-digit hex `const Color(0xAARRGGBB)`; a translucent design token bakes its alpha into the hex (`0x12FFFFFF` for white at 7%). JSON skins use `#RRGGBB` / `#AARRGGBB`.
- Override a derived slot only where its default does not hold. Do not re-declare a derived slot with the same value as the default.

### Adding a color

1. **Look for an existing slot first** — read `app_skin.dart`; the right slot often already exists under a component name.
2. **Prefer a derived slot.** If the color can be expressed from the base palette, add it to `AppSkin` with a default and a doc comment, so every skin inherits it. Then register it where the project keeps the slot lists: its name in `AppSkin.derivedSlotNames`, an override hook in `JsonSkin` (`@override Color get x => overrides['x'] ?? super.x;`), and the overridable list in `assets/skins/README.md`.
3. **Add a base slot only** when the color genuinely differs per skin and cannot be derived. Implement it in `LightSkin` **and** `DarkSkin` (the compiler enforces this), add its name to `AppSkin.baseSlotNames`, read it in `JsonSkin` (`@override Color get x => base['x']!;`), add it to the JSON template — and **add the key to every existing `assets/skins/*.json` file**, because the parser requires exactly the base slots and rejects an old file.
4. If a Material widget or package should also pick the color up, wire the slot into `AppTheme` too.
5. If the project has tests over the slot lists or the JSON parser, they fail until the lists and `JsonSkin` match `AppSkin` — run them.

### Skins are a list: registry, cubit, picker

- **`SkinRegistry`** holds `static const builtIns = <AppSkin>[LightSkin(), DarkSkin()]` plus every skin its `SkinSource`s load (an `AssetSkinSource` reads every valid `assets/skins/*.json`). It is a lazy singleton registered in core DI, and `await sl<SkinRegistry>().load()` runs in `main()` before `runApp`. A file that breaks a rule is skipped and logged, never half-applied; a duplicate id is skipped.
- **`SkinCubit(SkinRegistry registry)`** holds the active `AppSkin skin` and exposes `skins`. `select(skin)` persists the skin's `id` and its `themeMode` (through `CacheHelper`) and emits `SkinChangedState(skin)`. On launch it restores the saved id; if that skin is gone, it falls back to the registry's built-in of the saved mode (`registry.builtInFor(mode)`).
- `SkinCubit` is provided once, at the app root in `my_app.dart` (not in `app_router.dart`). Feature code switches with `context.selectSkin(skin)` (the `SkinSwitcherContext` extension) or opens the picker sheet (`showThemeSheet(context)`), which lists `cubit.skins`. Never read or write the theme cache keys outside `SkinCubit`, and never provide a second `SkinCubit`.
- `MaterialApp` takes **only** `theme: AppTheme.of(skin)` — no `darkTheme`, no `themeMode`; the chosen skin already decides light or dark.
- During the theme cross-fade the `ColorScheme` lerps while `AppTokens.skin` snaps at the midpoint. UI that must show the choice on the tap frame (a selected row in the picker) reads `context.read<SkinCubit>().skin` inside a `BlocBuilder<SkinCubit, SkinState>`, not `context.tokens.skin`.

```dart
MultiBlocProvider(
  providers: [BlocProvider(create: (context) => SkinCubit(sl<SkinRegistry>()))],
  child: BlocBuilder<SkinCubit, SkinState>(
    builder: (context, state) {
      final skin = context.read<SkinCubit>().skin;
      return ScreenUtilInit(
        designSize: const Size(375, 812),
        minTextAdapt: true,
        builder: (context, child) => MaterialApp(
          theme: AppTheme.of(skin),
          // ...
        ),
      );
    },
  ),
)
```

### Adding a skin

**Prefer JSON.** Drop a file into `assets/skins/` following the project's format (`assets/skins/README.md`): `id` (`[a-z0-9_-]+`, unique, not a built-in id), `mode` (`"light"` / `"dark"`), `name.en` (and optionally `name.ar`), `colors` with every base slot and nothing else, and optional `overrides` for derived slots. It appears in the picker with no Dart change. A dark JSON skin must override the derived slots `DarkSkin` overrides, or it gets light-tuned shadows and sheets that don't lift off the page.

A **Dart** skin is only for a new built-in: extend `AppSkin` with a unique `id` and a `displayName`, implement the base slots, add it to `SkinRegistry.builtIns`, and add a `const AppTokens` for it plus a branch in `AppTokens.of` like `light` / `dark`.

## Text styles — `tokens.text`

`AppTypography` is an `@immutable` class with `static const standard` and one `TextStyle` getter per style; the project's `AppText` renders them.

- Never a raw `TextStyle(fontSize: …)` or `Theme.of(context).textTheme.…` in presentation code — pick a getter.
- Prefer the semantic getters (`displayXl … displaySm`, `headingLg … headingSm`, `bodyLg … bodySm`, `caption`, `overline`, `codeMd`/`codeSm`, `badge`). Numeric `styleNNWeight` getters, where they still exist, are legacy — don't use them in new code.
- Styles carry no color: `tokens.text.bodyMd.copyWith(color: tokens.skin.textSecondary)`. `.copyWith` is also fine for a small tweak (weight from `FontWeightHelper`, `letterSpacing`, `decoration`, `fontStyle`); a different font size means a different getter.
- **Adding a style:** add one getter built with the class's own generator, weights from `FontWeightHelper`, families from `AppFonts` — never a family name typed as a string — with a `///` comment saying what it is for:

```dart
/// Uppercase section labels like 'PREFERENCES' — pair with
/// toUpperCase() at the call site.
TextStyle get overline => _textStyle(
      11,
      FontWeightHelper.medium,
      height: 1.3,
      tracking: 0.08,
    );
```

The generator is the only place `flutter_screenutil` scales type, the only place a font fallback is attached (so Arabic still renders in a Latin display or mono family), and where tracking in `em` becomes `letterSpacing`:

```dart
static TextStyle _textStyle(
  double size,
  FontWeight weight, {
  String? family,
  double? height,
  double tracking = 0,
}) {
  return TextStyle(
    fontSize: size.spMin,
    fontWeight: weight,
    fontFamily: family,
    fontFamilyFallback: family == null ? null : const [AppFonts.arabic],
    height: height,
    letterSpacing: tracking == 0 ? null : size.spMin * tracking,
  );
}
```

The app-wide default family and its fallback are set once, in `AppTheme` (`fontFamily: AppFonts.text, fontFamilyFallback: [AppFonts.arabic]`).

## Spacing, radii, shadows

- **`tokens.space`** — gaps and padding: `VerticalSpace(tokens.space.sm)`, `EdgeInsets.all(tokens.space.lg)`, `padding: tokens.space.screenH`. Values are `double`s.
- **`tokens.radius`** — `decoration: BoxDecoration(borderRadius: tokens.radius.card)`; for one corner, `Radius.circular(tokens.radius.xlValue)`. Prefer the semantic names (`card`, `input`, `button`, `sheet`) when they fit.
- **`tokens.elevation`** — `boxShadow: tokens.elevation.high`; a glowing CTA uses `tokens.elevation.glow()` (pass `color: tokens.skin.dangerGlow` for destructive). A genuinely one-off shadow may stay inline, but its color still comes from the skin.
- A missing step is a getter on the group's class with the exact value (`double get huge => 48;` in `AppSpacing`), documented — not a literal at the call site. Fixed sizes that are not spacing (an icon size, an avatar diameter) stay plain numbers at the call site.

## Motion — `tokens.motion`

`AppMotion` (`lib/core/theme/motion/app_motion.dart`) is an `@immutable` class with `static const standard` and one getter per token. Every animation picks its timing from it: **no `Duration(milliseconds: …)`, `Curves.x` or `Cubic(…)` for an animation outside `lib/core/theme/`.** A value that is not there is a missing token.

The tokens, by kind. This is the shape and naming to mirror; the numbers are one app's design, not defaults to copy (see "Adding a token" for where values come from):

```dart
@immutable
class AppMotion {
  const AppMotion();

  static const standard = AppMotion();

  /// Micro interactions: press states, border and color flips on chips
  /// and inputs. Example: a suggestion chip's border darkening on tap.
  Duration get fast => const Duration(milliseconds: 120);

  /// Standard transitions: fades, background shifts, tab label color.
  Duration get base => const Duration(milliseconds: 180);

  /// Entrances of content blocks. Example: a chat bubble appearing.
  Duration get slow => const Duration(milliseconds: 260);

  /// Big springy morphs. Example: the segmented thumb sliding between filters.
  Duration get emphasis => const Duration(milliseconds: 450);

  /// One full cycle of the typing indicator's three bouncing dots.
  Duration get typingLoop => const Duration(milliseconds: 1200);

  /// The default deceleration curve — fast start, gentle stop. Pairs with
  /// [fast]/[base] for most transitions.
  Curve get easeOut => const Cubic(0.22, 0.61, 0.36, 1);

  /// The symmetric curve for looping animations. Pairs with [typingLoop].
  Curve get easeInOut => const Cubic(0.65, 0, 0.35, 1);

  /// The overshoot curve giving entrances a playful bounce. Pairs with
  /// [slow]/[emphasis] for pops, sheets, and the segmented thumb.
  Curve get spring => const Cubic(0.34, 1.4, 0.64, 1);

  /// How far a fade-up entrance starts below its resting spot.
  double get fadeUpOffset => 10;

  /// The starting scale of a pop entrance. Example: the orb scaling in.
  double get popScale => 0.94;

  /// The delay before a single element's entrance starts.
  Duration get entranceLeadIn => const Duration(milliseconds: 60);

  /// The delay before the first item of a staggered group starts.
  Duration get staggerBase => const Duration(milliseconds: 120);

  /// The gap between consecutive items of a staggered group.
  Duration get staggerStep => const Duration(milliseconds: 40);

  /// The entrance delay for item [index] of a staggered group. Pass
  /// `leadIn: false` for a list the user is already looking at.
  Duration staggerAt(int index, {bool leadIn = true}) =>
      (leadIn ? staggerBase : Duration.zero) + staggerStep * index;

  /// The gap between beats of a decorative reveal — slower than a list stagger.
  Duration get revealStep => const Duration(milliseconds: 180);

  /// The delay for beat [index] of a decorative reveal.
  Duration revealAt(int index) => revealStep * index;

  /// Small components reacting to touch: chips, buttons, the segmented
  /// thumb. Example: a task card's press morph.
  Motion get pressSpring => const MaterialSpringMotion.expressiveSpatialFast();

  /// Large surfaces entering. Example: a bottom sheet springing up.
  Motion get surfaceSpring =>
      const MaterialSpringMotion.expressiveSpatialDefault();

  /// Exits and dismissals. Example: a sheet flung closed.
  Motion get exitSpring => const MaterialSpringMotion.standardSpatialFast();

  /// Non-spatial changes: color, opacity, elevation.
  Motion get effectsSpring =>
      const MaterialSpringMotion.standardEffectsDefault();
}
```

Using it:

```dart
final tokens = context.tokens;
AnimatedContainer(
  duration: tokens.motion.fast,
  curve: tokens.motion.easeOut,
  decoration: BoxDecoration(
    color: isSelected ? tokens.skin.chipBackground : tokens.skin.surface,
    borderRadius: tokens.radius.pill,
  ),
  child: child,
)
```

An `AnimationController` created in `initState`, or a cubit driving a `PageController`, has no theme to read — it takes its timing from `AppMotion.standard` (`duration: AppMotion.standard.slow`). That is the only place the static is used.

- Pair durations and curves the way the tokens' comments say: `fast`/`base` with `easeOut` for state changes, `slow`/`emphasis` with `spring` for entrances and pops, loops with `easeInOut`. Distances and scales (`fadeUpOffset`, `popScale`) come from `tokens.motion` too.
- A staggered group takes each item's delay from `tokens.motion.staggerAt(index)` (`leadIn: false` for a list already on screen); decorative layers use `revealAt(index)`; a single element uses `entranceLeadIn` — never `Duration(milliseconds: 40 * index)`.
- **Curve or spring.** A duration + curve runs a fixed length and restarts if interrupted; a spring (`motor`'s `Motion`, run with `SingleMotionBuilder` or a `MotionController`) carries release velocity and continues from wherever it is when retargeted. Use a spring token when a finger drives the motion — a press, drag or fling, or a value that can change mid-flight: `pressSpring` for touch, `surfaceSpring`/`exitSpring` for sheets and large surfaces, `effectsSpring` for color and opacity. Keep duration + curve for fixed-length, looping and staggered entrances. A spring is not automatically better (a short travel can settle loose), so do not convert an existing curve animation unless asked. Spring tokens need the `motor` package: use them only when it is already in `pubspec.yaml` or the user asks.
- Reuse the project's animation widgets in `lib/core/widgets/animation/` (a tap-bounce wrapper, fade-up / pop-in entrances, staggered list items) before writing a new `AnimationController`.
- Durations that are not animations — timeouts, debounce, polling, `Future.delayed`, how long a snackbar stays up — are not motion tokens; they stay at the call site or in the class that owns them.
- Route transitions are set once, in `ThemeData.pageTransitionsTheme` (for example `FadeForwardsPageTransitionsBuilder` on Android, while iOS keeps its platform back-swipe) — not per route. A `PageView` uses `physics: const SpringPagePhysics()` when the project has it.

**Adding a token:** reuse a role token (`fast`, `base`, `slow`, `emphasis`, the curves, the stagger helpers) whenever it fits; add a new getter only for a genuinely new timing, curve or distance. Name it for what it is for (`typingLoop`, `slideUpOffset`), not after one screen, and give it a `///` comment saying what it is for, what it pairs with, and `Example:` naming the real place. Values come from the project's design: an HTML prototype's CSS motion tokens and `@keyframes` (extract them the way `design-from-html-flutter` describes), a motion doc such as `docs/design/motion.md`, or the user. Only when the project has no design source, use the numbers in the reference set above. If the project has a `lib/core/theme/` layer without `app_motion.dart`, create it in this shape with only the tokens this change needs, add the `motion` group to `AppTokens` (see "Adding a token group"), and do not sweep existing inline durations into it unless the user asks. If the project has a test over the tokens, update it in the same change.

## Shapes — `tokens.shape`

`AppShapes` (from `material_shapes`) holds non-rectangular and morphing shapes as (resting, active) `RoundedPolygon` pairs plus an `xBorder(t)` that interpolates between them; drive `t` with `tokens.motion.pressSpring` for touch or `effectsSpring` for selection. Rectangle corners come from `tokens.radius`, not here. Take shapes only from `tokens.shape` (`AppShapes.standard` where there is no theme), never build a polygon in a widget, and do not put a morph shape on a widget unless the user asks — it changes how the app looks.

## `ThemeData` — `AppTheme`

```dart
abstract final class AppTheme {
  static ThemeData get light => _build(AppTokens.light);

  static ThemeData get dark => _build(AppTokens.dark);

  static ThemeData of(AppSkin skin) => _build(AppTokens.of(skin));

  static ThemeData _build(AppTokens tokens) { ... }
}
```

`AppTheme` is the only `ThemeData` builder; features never build one. `_build` sets `useMaterial3`, `extensions: [tokens]`, `brightness` from `skin.themeMode`, `scaffoldBackgroundColor`, `textSelectionTheme`, the default `fontFamily` and `fontFamilyFallback` from `AppFonts`, `pageTransitionsTheme`, and every component theme (`appBarTheme`, `dialogTheme`, `bottomSheetTheme`, `switchTheme`, `checkboxTheme`, `timePickerTheme`, …) — colors from skin slots (`skin.appBarBackground`, `barrierColor: skin.overlayBarrier`), text from `tokens.text`, radii from `tokens.radius`. `AppTokens.of(skin)` returns the `const` `light` / `dark` instances for the built-ins and caches one per id for other skins.

For the `ColorScheme`, **map every role explicitly** in `ColorScheme.fromSeed(seedColor: skin.primary, brightness: …, …)`. Any role left out is invented by Material's tonal-palette algorithm from the seed, and Material widgets and packages will draw with a color nobody chose. The usual mapping:

| ColorScheme role | AppSkin slot |
| --- | --- |
| `primary` / `onPrimary` | `primary` / `textOnPrimary` |
| `primaryContainer` / `onPrimaryContainer` | `primaryLight` / `primaryDark` |
| `inversePrimary`, `surfaceTint` | `primary` |
| `secondary`, `tertiary` / `onSecondary`, `onTertiary` | `accent` / `onAccent` (one accent hue: both share it) |
| `secondaryContainer`, `tertiaryContainer` / `on…Container` | `accentLight` / `accent` |
| `surface` / `onSurface` / `onSurfaceVariant` | `surface` / `textPrimary` / `textSecondary` |
| `surfaceContainerLowest` → `Highest` | the app's own elevation ladder: `card`, `background`, `surface`, `surfaceElevated`, `surfaceElevated` |
| `inverseSurface` / `onInverseSurface` | `inverseSurface` / `onInverseSurface` |
| `outline` / `outlineVariant` | `border` / `borderSubtle` |
| `error` / `onError` / `errorContainer` / `onErrorContainer` | `error` / `dangerButtonText` / `errorLight` / `error` |

**Do not map `shadow` or `scrim`.** `skin.shadow` and `skin.overlayBarrier` already bake their alpha in for direct use in a `BoxShadow` or a barrier, while Material composites `colorScheme.shadow`/`scrim` itself; mapping them flattens elevation app-wide. The rule: map roles used as-is (surfaces, text, borders, containers); never map a role Material alpha-composites when the slot already carries alpha.

If the project has a test that asserts the `ColorScheme` mapping for every skin, update it in the same change as the mapping.

## Adding a token group

1. Create `app_<group>.dart`: an `@immutable` class with a `const` constructor and `static const standard = …()` (or a skin-dependent constructor like `AppElevation(skin)`).
2. Add a `final` field to `AppTokens`, and set it in `light`, `dark`, `AppTokens.of`, `copyWith` and `lerp` (invariant groups pass `this.<group>` through; skin-dependent ones snap with the skin at the midpoint).
3. Extend the project's token test, then document the group in `lib/core/theme/README.md` if it has one.

## What NOT to do

- Do not write `Color(0x…)`, `Colors.x` (other than `Colors.transparent`), a literal radius or spacing, an inline `TextStyle(...)`, or an animation `Duration`/`Curves`/`Cubic` in feature or core-widget code — read or add a token.
- Do not read `context.tokens` in `initState`, `dispose`, a `late final` initializer, a constructor or a cubit — use `AppMotion.standard` / `AppShapes.standard` there, and only there.
- Do not cache `ThemeData` (`static final theme = AppTheme.light`), and do not override `Theme(data: …)` in a subtree.
- Do not read `Theme.of(context).colorScheme` or `Theme.of(context).textTheme` in the app's own widgets — use `context.tokens`, and reach package widgets through the app's wrappers.
- Do not use `.spMin` / `.r` / `.w` outside `AppTypography`.
- Do not put sizes, blur values, shadow lists or palettes on `AppSkin` — slots are colors.
- Do not branch on dark/light in a widget to pick a color — override the slot in the skin.
- Do not add a slot, style or token without a `///` doc comment saying what it is for.
- Do not add a base slot when a derived default would do, implement a new base slot in only one skin, or add one without updating every JSON skin file.
- Do not pass `darkTheme` or `themeMode` to `MaterialApp`, provide `SkinCubit` anywhere but the app root, or touch the theme cache keys outside `SkinCubit`.
- Do not hardcode a light/dark toggle — skins are a list; switch with `SkinCubit.select` / `context.selectSkin`, and add a skin as a JSON file.
- Do not leave a `ColorScheme` role to `fromSeed`, and do not map `shadow`/`scrim`.
- Do not change a style's `fontSize` with `.copyWith`, or type a font family as a string — pick or add an `AppTypography` getter and use `AppFonts`.
- Do not compute stagger delays by hand — use `staggerAt` / `revealAt`.
- Do not build a second `ThemeData`, a per-route transition, or a polygon shape in feature code.
