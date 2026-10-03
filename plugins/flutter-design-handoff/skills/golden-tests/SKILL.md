---
name: golden-tests
description: Golden tests that lock a Flutter screen's look with plain flutter_test — a shared harness (test/helpers/golden_harness.dart) that renders a screen headless at 375×812, ratio 2, through the app's own AppTheme.of(skin), EasyLocalization and ScreenUtil, with real fonts and real shadows; the real cubit fed by a mocked repository for each state; a variant matrix (the other skin, Arabic right-to-left, 2× text, a small phone); and the rule that a regenerated golden is looked at before it is committed. Use only when the user asks for golden or UI snapshot tests, right after a screen passes visual-verification, or when a golden test fails — not because a screen or widget was added or changed.
---

# Golden Tests

`visual-verification` proves a screen matches its design today; a golden is what stops it drifting tomorrow. Goldens here are plain `flutter_test` (`matchesGoldenFile`) — no golden package.

## Where they live

```
test/helpers/golden_harness.dart                                                  shared, once per project
test/feature/<feature>/presentation/<screen>_screen/ui/<screen>_golden_test.dart  mirrors lib/, as in flutter-testing
test/feature/<feature>/presentation/<screen>_screen/ui/goldens/*.png              committed
```

Tag every golden file `@Tags(['golden'])` and declare the tag once in `dart_test.yaml` (`tags:` → `golden:`). Goldens are generated and checked on one OS — font rasterization differs between macOS, Linux and Windows — so CI on another OS runs `flutter test --exclude-tags golden`. Add `failures/` to `.gitignore`.

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

## Writing one

The data comes the way the app gets it: the real cubit, fed by a mocked repository (mocktail, as in `flutter-testing`). The cubit's constructor fetch runs against the mock.

```dart
@Tags(['golden'])
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:<app>/core/data/api/global_response.dart';
import 'package:<app>/core/data/error_handling/failures/failure.dart';
import 'package:<app>/core/data/error_handling/result.dart';
import 'package:<app>/core/l10n/app_locales.dart';
import 'package:<app>/core/theme/skin/app_skin.dart';
import 'package:<app>/core/theme/skin/dark_skin.dart';
import 'package:<app>/core/theme/skin/light_skin.dart';
import 'package:<app>/feature/x/data/model/x_model.dart';
import 'package:<app>/feature/x/data/repository/x_repository.dart';
import 'package:<app>/feature/x/presentation/x_screen/logic/x_cubit.dart';
import 'package:<app>/feature/x/presentation/x_screen/ui/x_screen.dart';

import '../../../../../helpers/golden_harness.dart';

class _MockXRepository extends Mock implements XRepository {}

const _model = XModel(id: 1, title: 'Sample');

void main() {
  setUpAll(setUpGoldens);

  late _MockXRepository repository;
  setUp(() => repository = _MockXRepository());

  Future<void> golden(
    WidgetTester tester,
    String file, {
    AppSkin skin = const DarkSkin(),
    Locale locale = AppLocales.en,
    double textScale = 1,
    Size size = goldenDesignSize,
    EdgeInsets safeArea = goldenDesignSafeArea,
    Future<void> Function(XCubit cubit)? afterMount,
  }) async {
    final cubit = XCubit(repository);
    addTearDown(cubit.close);
    await expectScreenGolden(
      tester,
      BlocProvider.value(value: cubit, child: const XScreen()),
      file,
      skin: skin,
      locale: locale,
      textScale: textScale,
      size: size,
      safeArea: safeArea,
      afterMount: afterMount == null ? null : () => afterMount(cubit),
    );
  }

  group('loaded', () {
    setUp(() {
      when(() => repository.getX()).thenAnswer(
        (_) async => Result.success(const GlobalResponse(data: _model)),
      );
    });

    testWidgets(
      'dark, en',
      (tester) => golden(tester, 'goldens/x_loaded_dark_en.png'),
    );
    testWidgets(
      'light, en',
      (tester) => golden(
        tester,
        'goldens/x_loaded_light_en.png',
        skin: const LightSkin(),
      ),
    );
    testWidgets(
      'dark, ar',
      (tester) =>
          golden(tester, 'goldens/x_loaded_dark_ar.png', locale: AppLocales.ar),
    );
    testWidgets(
      'dark, en, 2x text',
      (tester) =>
          golden(tester, 'goldens/x_loaded_dark_en_text2x.png', textScale: 2),
    );
    testWidgets(
      'dark, en, small phone',
      (tester) => golden(
        tester,
        'goldens/x_loaded_dark_en_small.png',
        size: goldenSmallPhone,
        safeArea: goldenSmallPhoneSafeArea,
      ),
    );
  });

  testWidgets('loading, dark, en', (tester) async {
    when(() => repository.getX()).thenAnswer((_) => Completer<Never>().future);
    await golden(tester, 'goldens/x_loading_dark_en.png');
  });

  testWidgets('failure, dark, en', (tester) async {
    when(
      () => repository.getX(),
    ).thenAnswer((_) async => Result.failure(ServerFailure.noNetwork()));
    await golden(
      tester,
      'goldens/x_failure_dark_en.png',
      afterMount: (cubit) => cubit.getX(),
    );
  });
}
```

- **Loading** — a repository future that never completes. **Failure** — `Result.failure(ServerFailure.noNetwork())`, fetched again in `afterMount` so the screen's listener sees it and its snackbar is in the golden. `Result` and `ServerFailure` are imported from where the project keeps them in `lib/core/data/error_handling/`.
- **Fixed data** — fixed dates and text, nothing from `DateTime.now()`, no network images (they render blank in tests).
- A form the design shows filled in gets its cubit controllers filled before the capture (`cubit.emailController.text = …`).
- `DarkSkin` stands for the skin the design is drawn in.

## The matrix

Per screen, the main state gets five goldens; every other state gets the first one only.

| Variant | Why |
|---|---|
| The design's skin, `goldenDesignSize`, English | the reference — the golden `visual-verification` compared |
| The other built-in skin (`SkinRegistry.builtIns`) | a hardcoded color shows up here first |
| `AppLocales.ar` | right-to-left mirroring and the Arabic font |
| `textScale: 2` | the user's large-text setting |
| `goldenSmallPhone` (360×640) with `goldenSmallPhoneSafeArea` | the smallest supported screen |

The full cross-product is too many images to review. A variant that throws `A RenderFlex overflowed` is a real layout bug — fix it or report it; never drop the variant to make the test pass.

## Regenerating

```bash
flutter test --update-goldens test/feature/<feature>/presentation/<screen>_screen/ui/<screen>_golden_test.dart
```

That command always makes the tests pass, which is exactly why it is dangerous. Once a golden is committed:

- A failing golden first gets a question — was the change intended? Look at the images `flutter test` writes to `failures/` next to the test.
- Intended: regenerate, then open every changed PNG before committing. A golden that changed and nobody can say why is a bug being committed.
- After a Flutter upgrade, expect a few changed pixels: regenerate on purpose, look, commit.

In review, changed golden PNGs are changed code.

## Common mistakes

- A `MaterialApp` with an ad-hoc theme in each test. The golden then tests the wrapper, not the app's theme.
- `pumpAndSettle` on a screen with a spinner: it times out. The harness pumps a fixed time.
- Mocking the cubit and stubbing every getter. Feed the real cubit through its repository.
- Generating goldens on one OS and checking them on another.
