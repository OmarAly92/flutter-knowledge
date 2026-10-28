---
name: golden-tests
description: Use for Flutter golden/snapshot tests, failed baselines, design-workflow captures and regression variants across skins, RTL, large text and small phones; inspect regenerated images before acceptance.
---

# Golden Tests

For implementation, read the [project configuration contract](../flutter-init/references/configuration.md) before applying package-specific instructions. Keep its conventions and naming; adapt package-specific examples through the selected mechanics.

`visual-verification` proves a screen matches its design today; a golden is what stops it drifting tomorrow. Goldens here are plain `flutter_test` (`matchesGoldenFile`) — no golden package.

Source-backed rows in design-driven implementation must follow the [per-screen verification contract](../visual-verification/SKILL.md#required-completion-contract): capture a candidate, compare it against the original HTML/Figma reference, inspect the diff and report percentages before approving its baseline. Flutter-to-Flutter regression and source-design comparison are separate checks.

For direct regression-test requests, follow the [golden workflow](../flutter-knowledge/references/workflows.md) without requiring a design source. When visual verification requests a capture, return the artifact to its comparison loop; do not recursively restart source inspection.

## Where they live

```
test/helpers/golden_harness.dart                                                  shared, once per project
test/feature/<feature>/presentation/<screen>_screen/ui/<screen>_golden_test.dart  mirrors lib/, as in flutter-testing
test/feature/<feature>/presentation/<screen>_screen/ui/goldens/*.png              committed
```

Tag every golden file `@Tags(['golden'])` and declare the tag once in `dart_test.yaml` (`tags:` → `golden:`). Goldens are generated and checked on one OS — font rasterization differs between macOS, Linux and Windows — so CI on another OS runs `flutter test --exclude-tags golden`. Add `failures/` to `.gitignore`.

## Shared capture

Read [the shared capture reference](references/capture.md) for the harness used by both golden regression and design verification. Reuse the existing project harness and its configured package APIs. Its [capture readiness](references/capture.md#capture-readiness) check blocks a row whose fonts or glyphs cannot be shown; a blocked variant is reported, never baselined.

## Adaptive coverage and baseline handoff

Read [coverage and handoff](references/coverage-handoff.md) before selecting state rows or approving baselines. Inspect the actual source transitions and live screen/owner/field code to discover applicable states, then bind each to source comparison where a reference exists or inspected regression plus behavior where it does not. The helper checks a declared scoped ledger; it does not discover unvisited states. Missing/unsupported required states block completion.

After opening the actual PNGs, use the existing runner inspection and the handoff helper to preserve prior PNG/profile/review evidence, promote only eligible candidates, and run ordinary golden tests without `--update-goldens`. Keep source fidelity, local baseline approval, behavior and normal regression separate. Regression-only candidates may be locally approved for authorized UI work without another user confirmation, but never become source VERIFIED.

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

## Efficient inspection

Reuse the existing harness, capture required variants together where practical and keep full logs local. Triage every changed/new PNG through an overview, then open originals at full resolution when details cannot be assessed. Inspect narrow + Arabic + large-text interaction, keyboard and shared-consumer variants where relevant. An overview is not a weaker acceptance test; ambiguous/uninspected details block approval.

## The matrix

This is the default regression matrix, not a limit on source-design coverage. Capture every supplied reference variant required by `visual-verification`, including alternate skins/locales for non-main states. Add the following regression variants where supported by the project; the main state gets the supported full matrix and other states get their supplied source profiles plus relevant RTL/large-text/narrow/keyboard risk checks selected from inspected state/code behavior.

| Variant | Why |
|---|---|
| The design's skin, viewport and locale | the reference — the golden `visual-verification` compared |
| The other built-in skin (`SkinRegistry.builtIns`) | a hardcoded color shows up here first |
| `AppLocales.ar` | right-to-left mirroring and the Arabic font; blocked, not captured, while no loaded font has the glyphs |
| `textScale: 2` | the user's large-text setting |
| `goldenSmallPhone` (360×640) with `goldenSmallPhoneSafeArea` | the smallest supported screen |

The full cross-product is too many images to review. A variant that throws `A RenderFlex overflowed` is a real layout bug — fix it or report it; never drop the variant to make the test pass.

## Regenerating

Capture intended changes into per-attempt candidate paths with the existing runner, inspect them, and follow [the inspected handoff](references/coverage-handoff.md#promote-check-recover). `--update-goldens` is a camera operation; it can overwrite approved expectations when aimed at them and never proves fidelity or regression correctness. The handoff preserves prior baselines/profiles/reviews and runs a real ordinary check after promotion.

- A failing golden needs an intended-change decision. Open the PNGs written to `failures/` next to the test and retain the failed check.
- Intended: capture a new candidate, open every changed PNG, approve through the scoped coverage ledger, then check without updating. An unexplained change blocks approval.
- After a Flutter upgrade, regenerate deliberately on the same OS and inspect the changed pixels before approval.

In review, changed golden PNGs are changed code. Local baseline approval does not commit or publish anything.

## Common mistakes

- A `MaterialApp` with an ad-hoc theme in each test. The golden then tests the wrapper, not the app's theme.
- `pumpAndSettle` on a screen with a spinner: it times out. The harness pumps a fixed time.
- Mocking the cubit and stubbing every getter. Feed the real cubit through its repository. A design-only screen has no repository: pump it as built, with its static sample content and its UI-only cubit if it has one; never add a fake data source for the capture.
- Generating goldens on one OS and checking them on another.
