# Shared Flutter capture

Used by `golden-tests` and `visual-verification`. Read [project configuration](../../flutter-init/references/configuration.md). The example is the default stack: compose the same controlled capture with the project's selected state, localization, typography, router and cache APIs. Do not add an absent default library solely to make this example compile.

## The harness

If `test/helpers/golden_harness.dart` exists, use it. If not, create it: it is the project's widget-test wrapper (`EasyLocalization` + `ScreenUtilInit` + `AppTheme`) plus what a golden needs. Replace `<app>` with the `name:` in `pubspec.yaml`.

```dart
import 'dart:convert';

import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:<app>/core/data/cache/cache_helper.dart';
import 'package:<app>/core/l10n/app_locales.dart';
import 'package:<app>/core/router/app_router.dart';
import 'package:<app>/core/theme/app_theme.dart';
import 'package:<app>/core/theme/skin/app_skin.dart';
import 'package:shared_preferences/shared_preferences.dart';

const goldenDesignSize = Size(375, 812);
const goldenDesignSafeArea = EdgeInsets.only(top: 44, bottom: 34);
const goldenSmallPhone = Size(360, 640);
const goldenSmallPhoneSafeArea = EdgeInsets.only(top: 24);

Future<void> setUpGoldens() async {
  TestWidgetsFlutterBinding.ensureInitialized();
  SharedPreferences.setMockInitialValues({});
  await CacheHelper.init();
  await EasyLocalization.ensureInitialized();
  final manifest =
      json.decode(await rootBundle.loadString('FontManifest.json'))
          as List<dynamic>;
  for (final family in manifest.cast<Map<String, dynamic>>()) {
    final loader = FontLoader(family['family'] as String);
    for (final font
        in (family['fonts'] as List<dynamic>).cast<Map<String, dynamic>>()) {
      loader.addFont(rootBundle.load(font['asset'] as String));
    }
    await loader.load();
  }
}

Future<void> expectScreenGolden(
  WidgetTester tester,
  Widget screen,
  String goldenFile, {
  required AppSkin skin,
  Locale locale = AppLocales.en,
  double textScale = 1,
  Size size = goldenDesignSize,
  EdgeInsets safeArea = goldenDesignSafeArea,
  Future<void> Function()? afterMount,
}) async {
  final shadowsWereDisabled = debugDisableShadows;
  debugDisableShadows = false;
  try {
    tester.view.physicalSize = size * 2;
    tester.view.devicePixelRatio = 2;
    final inset = FakeViewPadding(
      top: safeArea.top * 2,
      bottom: safeArea.bottom * 2,
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
                builder: (context, child) => MediaQuery(
                  data: MediaQuery.of(
                    context,
                  ).copyWith(textScaler: TextScaler.linear(textScale)),
                  child: child!,
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
    await expectLater(find.byType(MaterialApp), matchesGoldenFile(goldenFile));
  } finally {
    debugDisableShadows = shadowsWereDisabled;
  }
}
```

Why each part is there:

- **`FontManifest.json`** — without it `flutter test` draws every glyph as a square, and the golden proves nothing about typography. Fonts load in golden files only, so other widget tests keep their text metrics.
- **`debugDisableShadows = false`** — `flutter test` turns shadows off by default (blur dropped, Material elevation drawn as an outline). The harness turns them on for the capture and restores the value before the test ends; they render the same on every run on one machine.
- **The safe area** — `padding` and `viewPadding` give the screen a phone's status bar and home indicator: 44 top and 34 bottom at 375×812 (an iPhone X-class screen), 24 top on the small phone. `SafeArea` and `AppScaffold` then place content where a phone does — and where a phone-frame design draws it.
- **`AppRouter`'s keys** — the app root mounts `AppRouter.navigationKey` and `AppRouter.scaffoldMessengerKey`, and the snackbar extension shows through the messenger key; mounted here too, a snackbar shown once the screen is up appears in its golden. A failure from the cubit's constructor fetch is emitted before the screen's `BlocListener` exists, so it shows none: fetch again in `afterMount`, which runs once the screen is mounted.
- **`runAsync` + fixed frames** — translations and SVGs load for real, then a fixed second of frames, enough for an entrance animation that starts a frame late. Not `pumpAndSettle`: a spinner never settles, and a fixed time gives the same frame every run.
- **`find.byType(MaterialApp)`** — the whole screen, 750×1624, the same size as a design reference.


For source-design verification, match the reference viewport through `size` and its insets through `safeArea`. This example uses DPR 2; adapt both physical size and pixel ratio together when the reference requires another DPR. Pass a candidate `goldenFile` path to protect an approved baseline, then follow the [verification contract](../../visual-verification/SKILL.md#required-completion-contract) before promoting it.

Reuse this harness rather than creating parallel wrappers. Keyboard verification must exercise actual focus/resize/scroll behavior; do not use tester.ensureVisible to make a capture appear correct when the claim is automatic keyboard avoidance. A deliberately scrolled-state capture may scroll, but label it and verify automatic behavior separately.

Before the full screen matrix, run the [core and capture preflight](../../visual-verification/references/preflight.md) on one representative row: assert the expected root and state with finders, check fonts, shadows, text wrapping and inputs, and keep every profile value explicit. For design suites, write candidate goldens under a per-attempt path supplied by `--dart-define=CAPTURE_ROUND`, so the [verification runner](../../visual-verification/references/runner.md) can run one Flutter process for all rows and preserve each attempt.
