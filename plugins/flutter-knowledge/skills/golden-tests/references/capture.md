# Shared Flutter capture

Used by `golden-tests` and `visual-verification`. Read [project configuration](../../flutter-init/references/configuration.md). The example is the default stack: compose the same controlled capture with the project's selected state, localization, typography, router and cache APIs. Do not add an absent default library solely to make this example compile.

## The harness

If `test/helpers/golden_harness.dart` exists, use it. If not, create it: it is the project's widget-test wrapper (`EasyLocalization` + `ScreenUtilInit` + `AppTheme`) plus what a golden needs. Replace `<app>` with the `name:` in `pubspec.yaml`. Copy [`capture_readiness.dart`](../scripts/capture_readiness.dart) unchanged to `test/helpers/capture_readiness.dart`; it needs only Flutter and `flutter_test`. An existing harness that lacks its font loading and readiness calls gets the same additions. Readiness holds only for a harness that actually calls `expectCaptureProfile` and `expectCaptureReady` before the PNG matcher; a harness without them bakes the test fallback font silently.

```dart
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:<app>/core/data/cache/cache_helper.dart';
import 'package:<app>/core/l10n/app_locales.dart';
import 'package:<app>/core/router/app_router.dart';
import 'package:<app>/core/theme/app_theme.dart';
import 'package:<app>/core/theme/skin/app_skin.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'capture_readiness.dart';

const goldenDesignSize = Size(375, 812);
const goldenDesignSafeArea = EdgeInsets.only(top: 44, bottom: 34);
const goldenSmallPhone = Size(360, 640);
const goldenSmallPhoneSafeArea = EdgeInsets.only(top: 24);

late CaptureFonts goldenFonts;

Future<void> setUpGoldens() async {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues({});
  await CacheHelper.init();
  await EasyLocalization.ensureInitialized();
  goldenFonts = await loadCaptureFonts();
}

Future<void> expectScreenGolden(
  WidgetTester tester,
  Widget screen,
  String goldenFile, {
  required AppSkin skin,
  Locale locale = AppLocales.en,
  double textScale = 1,
  double devicePixelRatio = 2,
  Size size = goldenDesignSize,
  EdgeInsets safeArea = goldenDesignSafeArea,
  Future<void> Function()? afterMount,
  String? readinessReport,
}) async {
  final shadowsWereDisabled = debugDisableShadows;
  debugDisableShadows = false;
  try {
    tester.view.physicalSize = size * devicePixelRatio;
    tester.view.devicePixelRatio = devicePixelRatio;
    final inset = FakeViewPadding(
      top: safeArea.top * devicePixelRatio,
      bottom: safeArea.bottom * devicePixelRatio,
    );
    tester.view.padding = inset;
    tester.view.viewPadding = inset;
    addTearDown(tester.view.reset);
    await tester.runAsync(() async {
      await tester.pumpWidget(
        EasyLocalization(
          supportedLocales: AppLocales.supported,
          path: AppLocales.path,
          fallbackLocale: AppLocales.fallback,
          startLocale: locale,
          saveLocale: false,
          child: Builder(
            builder: (context) => ScreenUtilInit(
              designSize: goldenDesignSize,
              minTextAdapt: true,
              builder: (context, _) => MaterialApp(
                debugShowCheckedModeBanner: false,
                navigatorKey: AppRouter.navigationKey,
                scaffoldMessengerKey: AppRouter.scaffoldMessengerKey,
                theme: AppTheme.of(skin),
                localizationsDelegates: context.localizationDelegates,
                supportedLocales: context.supportedLocales,
                locale: context.locale,
                builder: (context, child) => CaptureThemeScope(
                  fonts: goldenFonts,
                  child: MediaQuery(
                    data: MediaQuery.of(
                      context,
                    ).copyWith(textScaler: TextScaler.linear(textScale)),
                    child: child!,
                  ),
                ),
                home: screen,
              ),
            ),
          ),
        ),
      );
      await Future<void>.delayed(const Duration(milliseconds: 100));
    });
    await tester.pump();
    await afterMount?.call();
    for (var frame = 0; frame < 20; frame++) {
      await tester.pump(const Duration(milliseconds: 50));
    }
    expectCaptureProfile(
      tester.element(find.byType(Navigator).first),
      viewport: size,
      devicePixelRatio: devicePixelRatio,
      locale: locale,
      textScale: textScale,
      safeArea: safeArea,
    );
    expectCaptureReady(tester, goldenFonts, reportPath: readinessReport);
    await expectLater(find.byType(MaterialApp), matchesGoldenFile(goldenFile));
  } finally {
    debugDisableShadows = shadowsWereDisabled;
  }
}
```

Why each part is there:

- **`loadCaptureFonts`** — `flutter test` runs the engine with `--use-test-fonts --disable-asset-fonts`: every glyph is a square of the Ahem test font unless a family is loaded and named by the text style. It loads the project's `FontManifest.json` families (bundled text and icon fonts), the installed SDK's Roboto and MaterialIcons when the project does not declare them, and any explicit `CaptureFontFile`. Fonts load in golden files only, so other widget tests keep their text metrics.
- **`CaptureThemeScope`, `expectCaptureProfile`, `expectCaptureReady`** — see [capture readiness](#capture-readiness). The profile check asserts what the camera applied instead of trusting the declaration, and the readiness check runs before any PNG is compared or written.
- **`debugDisableShadows = false`** — `flutter test` turns shadows off by default (blur dropped, Material elevation drawn as an outline). The harness turns them on for the capture and restores the value before the test ends; they render the same on every run on one machine.
- **The safe area** — `padding` and `viewPadding` give the screen a phone's status bar and home indicator: 44 top and 34 bottom at 375×812 (an iPhone X-class screen), 24 top on the small phone. `SafeArea` and `AppScaffold` then place content where a phone does — and where a phone-frame design draws it.
- **`AppRouter`'s keys** — the app root mounts `AppRouter.navigationKey` and `AppRouter.scaffoldMessengerKey`, and the snackbar extension shows through the messenger key; mounted here too, a snackbar shown once the screen is up appears in its golden. A failure from the cubit's constructor fetch is emitted before the screen's `BlocListener` exists, so it shows none: fetch again in `afterMount`, which runs once the screen is mounted.
- **`runAsync` + fixed frames** — translations and SVGs load for real, then a fixed second of frames, enough for an entrance animation that starts a frame late. Not `pumpAndSettle`: a spinner never settles, and a fixed time gives the same frame every run.
- **`find.byType(MaterialApp)`** — the whole screen, 750×1624, the same size as a design reference.


For source-design verification, match the reference viewport through `size` and its insets through `safeArea`. The default is DPR 2 (750×1624 at 375×812); pass `devicePixelRatio` for another reference, with `size` and `safeArea` in logical pixels. Pass a candidate `goldenFile` path to protect an approved baseline, then follow the [verification contract](../../visual-verification/SKILL.md#required-completion-contract) before promoting it.

Reuse this harness rather than creating parallel wrappers. Keyboard verification must exercise actual focus/resize/scroll behavior; do not use tester.ensureVisible to make a capture appear correct when the claim is automatic keyboard avoidance. A deliberately scrolled-state capture may scroll, but label it and verify automatic behavior separately.

Before the full screen matrix, run the [core and capture preflight](../../visual-verification/references/preflight.md) on one representative row: assert the expected root and state with finders, pass the [readiness check](#capture-readiness), check shadows, text wrapping and inputs, and keep every profile value explicit. For design suites, write candidate goldens under a per-attempt path supplied by `--dart-define=CAPTURE_ROUND`, so the [verification runner](../../visual-verification/references/runner.md) can run one Flutter process for all rows and preserve each attempt.

For adaptive state selection and inspected candidate-to-baseline promotion, read [coverage and handoff](coverage-handoff.md). The existing source reader discovers source variants; inspect owner/field/listener code and drive actual controls for additional relevant states. Missing references create regression rows, not source VERIFIED claims. The main state retains its supported matrix; add relevant combined RTL/large-text/narrow/keyboard cases without multiplying every state by every profile.

Keep the same camera and harness for candidates and normal regression. In a design suite, a nonempty `CAPTURE_ROUND` chooses `goldens/candidates/<round>/<row>.png`; without it, choose the approved `goldens/<row>.png` path. The ordinary test must run every declared named state test with `matchesGoldenFile`, rather than skip when the define is absent. The handoff validates inspected evidence, preserves prior baseline/profile/review bytes, copies accepted candidates and immediately checks without `--update-goldens`. Numeric PASS, candidate regeneration and baseline approval are separate from source fidelity and normal regression.

## Capture readiness

`expectCaptureReady` inspects every `RenderParagraph` and `RenderEditable` of the mounted capture (icons are text too) and returns `READY` or `BLOCKED` with the finding, the offending text and its widget chain. A blocked capture throws before the PNG is compared or written, so it can never become a baseline or a promotion candidate.

| Finding | Meaning | Handling |
| --- | --- | --- |
| `defaultFamily` (blocker) | The effective text style has no family; `flutter test` draws it in Ahem blocks. A loaded font cannot take its place: loading `Roboto`, `Ahem`, an empty name or a `fontFamilyFallback` all leave it blocked; only an explicit family renders. | Usually a replaced default style such as `AppBarTheme.titleTextStyle` built from typography tokens whose family is null. `CaptureThemeScope` fills the null family of the theme's text slots with the loaded stand-in, for the capture only. Production theme, tokens and fonts stay unchanged; never add a family to them to satisfy a test. |
| `unloadedFamily` (blocker) | A named family was never loaded. | Declare the font in the project's `pubspec.yaml` assets, or pass an explicit `CaptureFontFile` only for a font the user or project already supplied. Do not download fonts or substitute a look-alike. |
| `missingGlyph` (blocker) | No loaded font in the style's family chain has a nonblank glyph for a rendered code point. | Same as above; Arabic needs an Arabic-capable font actually in the chain. Roboto has none. Without one the Arabic rows are blocked, not captured. |
| `unverifiableCoverage` (blocker) | A loaded font's `cmap` could not be read (collection or unsupported format). | Treat as unproven; supply a readable font file. |
| `noText` (blocker) | No text was found in the capture root, so nothing was inspected. | Fix the mount or pass `requireText: false` for a screen that really has none. |
| `weightNotProvided`, `italicNotProvided`, `unloadedFallback` (warning) | The requested weight/style is approximated, or an unused fallback is unloaded. | Report in the evidence and inspect the PNG. A bold title in a family with only a Regular face is a visible mismatch to fix or report as DIFF, not a pass. |

The stand-in is the SDK's Roboto, which is also the default Android family; it replaces the platform default only in the capture. Record the stand-in and `CaptureFonts.repairs` (`fonts.toJson()`) in the evidence. If the design's text uses another family, typography stays NOT VERIFIED however clean the readiness result is. Weights and italics come from each font file's OS/2 table, not from `pubspec.yaml` `weight:`/`style:` entries, so a manifest entry that disagrees with its file is not detected.

`CaptureThemeScope` fills a fixed list of theme text slots: text themes, app bar, snackbar, dialog, tooltip, list tile, tab bar, bottom navigation, chip and button styles. A text style it does not list (navigation bar, menus, badge, popup, pickers) with no family stays blocked as `defaultFamily`, with its widget chain; fix it by adding that one slot to `captureTheme`, never by giving production a family or loading an arbitrary font. Input decoration styles are left alone because they inherit the text theme's family. State-resolved styles keep their resolvers.

What this proves: every rendered text run resolves to a loaded family and every code point has a glyph in a loaded font's `cmap`, and only when the harness ran `expectCaptureReady` and `expectCaptureProfile` before the matcher. The preflight evidence includes the JSON written by `reportPath` (status `READY`) and the passing log of that test; a missing report, or a harness lacking either call, leaves readiness unproven. What it does not prove: that a shared wrapper matches the source, glyph shapes, shaping or joining, kerning, weight fidelity, text drawn outside paragraphs (custom painters, SVG, images) or that the source uses the same font. Inspect the PNG for those. A passing load is never proof of glyph support.

Run it on one representative row per profile before the matrix, including an Arabic row whenever Arabic rows are planned, and keep the readiness output in the evidence directory. A blocked row stays in the coverage ledger as `unsupported` with the finding as its reason; it is neither silently dropped nor given a baseline. The camera of a batch fails when any row is blocked, so resolve or exclude blocked rows before the batch, never after.

A harness that mounts the real application root cannot receive `CaptureThemeScope`. Compose the controlled `MaterialApp` above with the application's own router instead of editing production code: for a screen whose providers the route owns, pass `onGenerateRoute: AppRouter.generateRoute` and `onGenerateInitialRoutes: (name) => [AppRouter.generateRoute(RouteSettings(name: name))]` (otherwise a nested initial route is split into its parent routes). `expectCaptureReady(..., reportPath:)` writes the JSON report even when it throws.
