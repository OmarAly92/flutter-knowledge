import 'dart:convert';
import 'dart:io';

import 'package:core_reference_check/core/capture_consumers.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers/capture_readiness.dart';

Future<void> pumpBar(
  WidgetTester tester,
  CaptureFonts fonts, {
  required bool scoped,
  String title = 'Notifications',
}) async {
  tester.view.physicalSize = const Size(375, 812);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    MaterialApp(
      theme: CaptureFixtureTheme.light,
      builder: scoped
          ? (context, child) => CaptureThemeScope(fonts: fonts, child: child!)
          : null,
      home: Scaffold(
        appBar: CaptureFixtureAppbar(titleText: title),
        body: const Center(child: CaptureFixtureText('Body text')),
      ),
    ),
  );
  await tester.pump();
}

Future<void> pumpText(WidgetTester tester, Widget child) async {
  await tester.pumpWidget(
    Directionality(
      textDirection: TextDirection.ltr,
      child: Center(child: child),
    ),
  );
}

Set<String> kinds(Iterable<ReadinessFinding> findings) =>
    findings.map((finding) => finding.kind).toSet();

Uint8List cmapFont(int format, int subtableLength) {
  final bytes = Uint8List(40 + subtableLength);
  final data = ByteData.sublistView(bytes);
  data.setUint32(0, 0x00010000);
  data.setUint16(4, 1);
  for (var i = 0; i < 4; i++) {
    data.setUint8(12 + i, 'cmap'.codeUnitAt(i));
  }
  data.setUint32(20, 28);
  data.setUint16(30, 1);
  data.setUint16(32, 3);
  data.setUint16(34, 1);
  data.setUint32(36, 12);
  if (subtableLength >= 2) data.setUint16(40, format);
  return bytes;
}

Future<String?> hintFamily(
  WidgetTester tester,
  ThemeData theme,
  String hint,
) async {
  await tester.pumpWidget(
    MaterialApp(
      theme: theme,
      home: Scaffold(
        body: TextField(decoration: InputDecoration(hintText: hint)),
      ),
    ),
  );
  await tester.pumpAndSettle();
  return paragraph(tester, hint).text.style?.fontFamily;
}

RenderParagraph paragraph(WidgetTester tester, String text) => find
    .byType(RichText)
    .evaluate()
    .map((element) => element.renderObject)
    .whereType<RenderParagraph>()
    .where((render) => render.text.toPlainText() == text)
    .first;

void main() {
  late CaptureFonts fonts;
  late String sdk;

  setUpAll(() async {
    TestWidgetsFlutterBinding.ensureInitialized();
    sdk = captureSdkFontDirectory()!;
    fonts = await loadCaptureFonts(
      files: [
        CaptureFontFile('ProjectSans', '$sdk/RobotoCondensed-Regular.ttf'),
      ],
    );
  });

  group('font coverage', () {
    FontCoverage coverageOf(String name) =>
        FontCoverage.parse(File('$sdk/$name').readAsBytesSync())!;

    test('Roboto covers its scripts and nothing outside them', () {
      final roboto = coverageOf('Roboto-Regular.ttf');
      expect(roboto.weight, 400);
      expect(roboto.italic, isFalse);
      expect(coverageOf('Roboto-Bold.ttf').weight, 700);
      expect(coverageOf('Roboto-Italic.ttf').italic, isTrue);
      for (final sample in ['A', 'z', '7', 'é', 'Ж', 'Ω']) {
        expect(roboto.covers(sample.runes.first), isTrue, reason: sample);
      }
      for (final sample in ['خ', 'ا', '你', '😀']) {
        expect(roboto.covers(sample.runes.first), isFalse, reason: sample);
      }
    });

    test('Material icon font covers exactly the SDK codepoints', () {
      final icons = coverageOf('MaterialIcons-Regular.otf');
      final listed = File('$sdk/codepoints')
          .readAsLinesSync()
          .where((line) => line.trim().isNotEmpty)
          .map((line) => int.parse(line.split(' ').last, radix: 16))
          .toList();
      expect(listed.length, greaterThan(1000));
      expect(listed.where((point) => !icons.covers(point)), isEmpty);
      expect(icons.covers('A'.runes.first), isFalse);
      expect(icons.covers(0x0627), isFalse);
    });

    test('unreadable font data has no coverage claim', () {
      expect(FontCoverage.parse(Uint8List.fromList([1, 2, 3])), isNull);
      expect(
        FontCoverage.parse(Uint8List.fromList(List.filled(64, 0))),
        isNull,
      );
    });
  });

  group('actual shared app bar consumer', () {
    testWidgets('title with no effective family is blocked before capture', (
      tester,
    ) async {
      await pumpBar(tester, fonts, scoped: false);
      final readiness = inspectCapture(tester, fonts);
      expect(readiness.ready, isFalse);
      expect(kinds(readiness.blockers), {'defaultFamily'});
      expect(readiness.blockers.single.detail, contains('Notifications'));
      expect(readiness.blockers.single.where, contains('CaptureFixtureText'));
      expect(
        () => expectCaptureReady(tester, fonts),
        throwsA(
          isA<TestFailure>().having(
            (failure) => failure.message,
            'message',
            contains('CAPTURE READINESS BLOCKED'),
          ),
        ),
      );
    });

    testWidgets('capture theme resolves it without touching the app theme', (
      tester,
    ) async {
      final productionTitle =
          CaptureFixtureTheme.light.appBarTheme.titleTextStyle;
      await pumpBar(tester, fonts, scoped: true);
      final readiness = expectCaptureReady(tester, fonts);
      expect(readiness.familiesUsed, contains('Roboto'));
      expect(fonts.repairs, contains('appBarTheme.titleTextStyle'));
      expect(productionTitle!.fontFamily, isNull);
      expect(
        CaptureFixtureTheme.light.appBarTheme.titleTextStyle!.fontFamily,
        isNull,
      );
    });

    testWidgets('a project family declared in the theme is left alone', (
      tester,
    ) async {
      final theme = CaptureFixtureTheme.light.copyWith(
        appBarTheme: const AppBarTheme(
          titleTextStyle: TextStyle(fontSize: 20, fontFamily: 'ProjectSans'),
        ),
      );
      final before = fonts.repairs.toSet();
      expect(
        captureTheme(theme, fonts).appBarTheme.titleTextStyle!.fontFamily,
        'ProjectSans',
      );
      expect(fonts.repairs.difference(before), isEmpty);
    });

    testWidgets('without any loaded stand-in the repair is a no-op', (
      tester,
    ) async {
      final empty = await tester.runAsync(
        () => loadCaptureFonts(standIn: 'NotLoadedAnywhere'),
      );
      expect(empty!.standIn, isNull);
      final theme = captureTheme(CaptureFixtureTheme.light, empty);
      expect(theme.appBarTheme.titleTextStyle!.fontFamily, isNull);
    });
  });

  group('families, icons and scripts', () {
    testWidgets('bundled custom family from an explicit file is ready', (
      tester,
    ) async {
      await pumpText(
        tester,
        const Text('Project text', style: TextStyle(fontFamily: 'ProjectSans')),
      );
      final readiness = expectCaptureReady(tester, fonts);
      expect(readiness.familiesUsed, {'ProjectSans'});
      expect(
        (fonts.toJson()['families'] as Map)['ProjectSans'].single['source'],
        startsWith('file:'),
      );
    });

    testWidgets('an undeclared family is blocked', (tester) async {
      await pumpText(
        tester,
        const Text('Branded', style: TextStyle(fontFamily: 'BrandSans')),
      );
      expect(kinds(inspectCapture(tester, fonts).blockers), {'unloadedFamily'});
    });

    testWidgets('an unloaded fallback is a warning, not proof', (tester) async {
      await pumpText(
        tester,
        const Text(
          'Fallback',
          style: TextStyle(
            fontFamily: 'Roboto',
            fontFamilyFallback: ['NotoSansArabic'],
          ),
        ),
      );
      final readiness = inspectCapture(tester, fonts);
      expect(readiness.ready, isTrue);
      expect(kinds(readiness.warnings), {'unloadedFallback'});
    });

    testWidgets('bundled icon glyphs are covered', (tester) async {
      await pumpText(tester, const Icon(Icons.arrow_back));
      final readiness = expectCaptureReady(tester, fonts);
      expect(readiness.familiesUsed, {'MaterialIcons'});
      expect(
        (fonts.toJson()['families'] as Map)['MaterialIcons'].single['source'],
        startsWith('asset:'),
      );
    });

    testWidgets('a missing icon glyph and an unloaded icon font are blocked', (
      tester,
    ) async {
      await pumpText(
        tester,
        const Icon(IconData(0x41, fontFamily: 'MaterialIcons')),
      );
      expect(kinds(inspectCapture(tester, fonts).blockers), {'missingGlyph'});
      await pumpText(
        tester,
        const Icon(IconData(0xe092, fontFamily: 'ProjectIcons')),
      );
      expect(kinds(inspectCapture(tester, fonts).blockers), {'unloadedFamily'});
    });

    testWidgets('Arabic and other uncovered scripts block the capture', (
      tester,
    ) async {
      await pumpText(
        tester,
        const Directionality(
          textDirection: TextDirection.rtl,
          child: Text('الإشعارات', style: TextStyle(fontFamily: 'Roboto')),
        ),
      );
      final readiness = inspectCapture(tester, fonts);
      expect(readiness.ready, isFalse);
      expect(kinds(readiness.blockers), {'missingGlyph'});
      expect(readiness.blockers.single.detail, contains('U+0627'));
      await pumpText(
        tester,
        const Text('你好', style: TextStyle(fontFamily: 'Roboto')),
      );
      expect(kinds(inspectCapture(tester, fonts).blockers), {'missingGlyph'});
    });

    testWidgets('Cyrillic and Greek are covered by the same check', (
      tester,
    ) async {
      await pumpText(
        tester,
        const Text('Привет Ω', style: TextStyle(fontFamily: 'Roboto')),
      );
      expectCaptureReady(tester, fonts);
    });

    testWidgets('a font with unreadable data cannot claim coverage', (
      tester,
    ) async {
      final directory = Directory.systemTemp.createTempSync('capture_font_');
      addTearDown(() => directory.deleteSync(recursive: true));
      final bad = File('${directory.path}/bad.ttf')
        ..writeAsBytesSync(List.filled(64, 0));
      final loaded = await tester.runAsync(
        () => loadCaptureFonts(files: [CaptureFontFile('BadSans', bad.path)]),
      );
      await pumpText(
        tester,
        const Text('Bad', style: TextStyle(fontFamily: 'BadSans')),
      );
      expect(kinds(inspectCapture(tester, loaded!).blockers), {
        'unverifiableCoverage',
      });
    });

    testWidgets('rich text spans inherit the effective family', (tester) async {
      await pumpText(
        tester,
        const Text.rich(
          TextSpan(
            style: TextStyle(fontFamily: 'Roboto'),
            children: [
              TextSpan(text: 'Latin '),
              TextSpan(
                text: 'خ',
                style: TextStyle(fontWeight: FontWeight.w700),
              ),
            ],
          ),
        ),
      );
      expect(kinds(inspectCapture(tester, fonts).blockers), {'missingGlyph'});
    });
  });

  group('weights and evidence', () {
    testWidgets('a requested weight the family lacks is a warning', (
      tester,
    ) async {
      await pumpText(
        tester,
        const Text(
          'Condensed bold',
          style: TextStyle(
            fontFamily: 'ProjectSans',
            fontWeight: FontWeight.w700,
          ),
        ),
      );
      final readiness = expectCaptureReady(tester, fonts);
      expect(kinds(readiness.warnings), {'weightNotProvided'});
    });

    testWidgets('a capture with no rendered text proves nothing', (
      tester,
    ) async {
      await tester.pumpWidget(const SizedBox.shrink());
      expect(kinds(inspectCapture(tester, fonts).blockers), {'noText'});
      expect(inspectCapture(tester, fonts, requireText: false).ready, isTrue);
    });

    testWidgets('the report is written before a blocked capture throws', (
      tester,
    ) async {
      final directory = Directory.systemTemp.createTempSync('capture_report_');
      addTearDown(() => directory.deleteSync(recursive: true));
      final report = '${directory.path}/nested/readiness.json';
      await pumpText(
        tester,
        const Text('Unstyled', style: TextStyle(fontSize: 12)),
      );
      expect(
        () => expectCaptureReady(tester, fonts, reportPath: report),
        throwsA(isA<TestFailure>()),
      );
      final saved = json.decode(File(report).readAsStringSync()) as Map;
      expect(saved['status'], 'BLOCKED');
      expect(saved['findings'].single['kind'], 'defaultFamily');
      expect(saved['fonts']['families'], contains('Roboto'));
    });
  });

  group('theme preservation', () {
    final stateStyle = WidgetStateTextStyle.resolveWith(
      (states) => TextStyle(
        color: states.contains(WidgetState.error) ? Colors.red : Colors.green,
        fontSize: states.contains(WidgetState.focused) ? 24 : 16,
        fontFamily: states.contains(WidgetState.error) ? 'ProjectSans' : null,
      ),
    );

    test('a state-resolved style keeps its resolver and every state', () {
      fonts.repairs.remove('chipTheme.labelStyle');
      final captured = captureTheme(
        ThemeData(chipTheme: ChipThemeData(labelStyle: stateStyle)),
        fonts,
      ).chipTheme.labelStyle!;
      expect(captured, isA<WidgetStateTextStyle>());
      expect(identical(captured, stateStyle), isFalse);
      const expected = {
        <WidgetState>{}: (Colors.green, 16.0, 'Roboto'),
        {WidgetState.error}: (Colors.red, 16.0, 'ProjectSans'),
        {WidgetState.focused}: (Colors.green, 24.0, 'Roboto'),
        {WidgetState.error, WidgetState.focused}: (
          Colors.red,
          24.0,
          'ProjectSans',
        ),
      };
      for (final entry in expected.entries) {
        final resolved = WidgetStateProperty.resolveAs<TextStyle>(
          captured,
          entry.key,
        );
        expect(resolved.color, entry.value.$1, reason: '${entry.key}');
        expect(resolved.fontSize, entry.value.$2, reason: '${entry.key}');
        expect(resolved.fontFamily, entry.value.$3, reason: '${entry.key}');
      }
      expect(fonts.repairs, contains('chipTheme.labelStyle'));
      expect(stateStyle.resolve({}).fontFamily, isNull);
    });

    testWidgets('button text styles keep per-state values when rendered', (
      tester,
    ) async {
      final theme = ThemeData(
        textButtonTheme: TextButtonThemeData(
          style: ButtonStyle(
            textStyle: WidgetStateProperty.resolveWith(
              (states) => TextStyle(
                fontSize: states.contains(WidgetState.disabled) ? 12 : 20,
              ),
            ),
          ),
        ),
      );
      await tester.pumpWidget(
        MaterialApp(
          theme: captureTheme(theme, fonts),
          home: Scaffold(
            body: Column(
              children: [
                TextButton(onPressed: () {}, child: const Text('Enabled')),
                const TextButton(onPressed: null, child: Text('Disabled')),
              ],
            ),
          ),
        ),
      );
      final enabled = paragraph(tester, 'Enabled').text.style!;
      final disabled = paragraph(tester, 'Disabled').text.style!;
      expect(enabled.fontSize, 20);
      expect(disabled.fontSize, 12);
      expect(enabled.fontFamily, 'Roboto');
      expect(disabled.fontFamily, 'Roboto');
      expectCaptureReady(tester, fonts);
    });

    testWidgets('input styles are left to the text theme they inherit from', (
      tester,
    ) async {
      final branded = ThemeData(
        fontFamily: 'ProjectSans',
        inputDecorationTheme: const InputDecorationTheme(
          hintStyle: TextStyle(color: Colors.green),
        ),
      );
      fonts.repairs.clear();
      final captured = captureTheme(branded, fonts);
      expect(
        fonts.repairs.where((slot) => slot.startsWith('inputDecorationTheme')),
        isEmpty,
      );
      expect(
        identical(
          captured.inputDecorationTheme.hintStyle,
          branded.inputDecorationTheme.hintStyle,
        ),
        isTrue,
      );
      expect(await hintFamily(tester, branded, 'Branded hint'), 'ProjectSans');
      expect(await hintFamily(tester, captured, 'Branded hint'), 'ProjectSans');
    });

    testWidgets('an unbranded input still gets the captured default', (
      tester,
    ) async {
      final plain = ThemeData().copyWith(
        textTheme: const TextTheme(bodyLarge: TextStyle(fontSize: 16)),
        inputDecorationTheme: const InputDecorationTheme(
          hintStyle: TextStyle(color: Colors.green),
        ),
      );
      expect(await hintFamily(tester, plain, 'Plain hint'), isNull);
      expect(
        await hintFamily(tester, captureTheme(plain, fonts), 'Plain hint'),
        'Roboto',
      );
    });

    testWidgets('state-resolved input labels render like production', (
      tester,
    ) async {
      final theme = ThemeData(
        inputDecorationTheme: InputDecorationTheme(labelStyle: stateStyle),
      );
      Future<TextStyle> label(ThemeData data) async {
        await tester.pumpWidget(
          MaterialApp(
            theme: data,
            home: const Scaffold(
              body: TextField(
                decoration: InputDecoration(
                  labelText: 'State label',
                  errorText: 'Bad',
                ),
              ),
            ),
          ),
        );
        await tester.pumpAndSettle();
        return paragraph(tester, 'State label').text.style!;
      }

      final production = await label(theme);
      final captured = await label(captureTheme(theme, fonts));
      expect(production.color, Colors.red);
      expect(captured.color, production.color);
      expect(captured.fontSize, production.fontSize);
      expect(captured.fontFamily, production.fontFamily);
    });
  });

  group('malformed font tables', () {
    test('a truncated format 4 header is rejected, not thrown', () {
      expect(FontCoverage.parse(cmapFont(4, 2)), isNull);
    });

    test('a truncated format 12 header is rejected, not thrown', () {
      expect(FontCoverage.parse(cmapFont(12, 2)), isNull);
    });

    test('a header that stops short of its first field is rejected', () {
      for (final format in [4, 12]) {
        for (final length in [0, 1, 4, 12, 15]) {
          expect(
            FontCoverage.parse(cmapFont(format, length)),
            isNull,
            reason: 'format $format with $length bytes',
          );
        }
      }
    });

    test('counts that run past the data claim no glyphs', () {
      final segments = cmapFont(4, 16);
      ByteData.sublistView(segments).setUint16(46, 0xFFFE);
      final groups = cmapFont(12, 16);
      ByteData.sublistView(groups).setUint32(52, 0x7FFFFFFF);
      for (final bytes in [segments, groups]) {
        final coverage = FontCoverage.parse(bytes);
        expect(coverage, isNotNull);
        for (final point in [0x41, 0x627, 0x1F600]) {
          expect(coverage!.covers(point), isFalse);
        }
      }
    });

    testWidgets('a truncated font is an unverifiable blocker, not an error', (
      tester,
    ) async {
      final directory = Directory.systemTemp.createTempSync('capture_cmap_');
      addTearDown(() => directory.deleteSync(recursive: true));
      final files = [
        for (final format in [4, 12])
          File('${directory.path}/cut$format.ttf')
            ..writeAsBytesSync(cmapFont(format, 2)),
      ];
      final loaded = await tester.runAsync(
        () => loadCaptureFonts(
          files: [
            CaptureFontFile('CutFour', files[0].path),
            CaptureFontFile('CutTwelve', files[1].path),
          ],
        ),
      );
      for (final family in ['CutFour', 'CutTwelve']) {
        await pumpText(
          tester,
          Text('Cut', style: TextStyle(fontFamily: family)),
        );
        expect(kinds(inspectCapture(tester, loaded!).blockers), {
          'unverifiableCoverage',
        }, reason: family);
      }
    });
  });

  group('profile', () {
    testWidgets('matching and mismatched profiles', (tester) async {
      tester.view.physicalSize = const Size(750, 1624);
      tester.view.devicePixelRatio = 2;
      tester.view.padding = const FakeViewPadding(top: 88, bottom: 68);
      addTearDown(tester.view.reset);
      late BuildContext context;
      await tester.pumpWidget(
        MaterialApp(
          home: Builder(
            builder: (inner) {
              context = inner;
              return const SizedBox.shrink();
            },
          ),
        ),
      );
      void profile({
        Size viewport = const Size(375, 812),
        double dpr = 2,
        double textScale = 1,
        EdgeInsets safeArea = const EdgeInsets.only(top: 44, bottom: 34),
        Locale locale = const Locale('en', 'US'),
        bool shadows = false,
      }) => expectCaptureProfile(
        context,
        viewport: viewport,
        devicePixelRatio: dpr,
        locale: locale,
        textScale: textScale,
        safeArea: safeArea,
        shadows: shadows,
      );
      profile();
      for (final mismatch in <String, void Function()>{
        'viewport': () => profile(viewport: const Size(360, 640)),
        'devicePixelRatio': () => profile(dpr: 1),
        'textScale': () => profile(textScale: 2),
        'safeArea': () => profile(safeArea: EdgeInsets.zero),
        'locale': () => profile(locale: const Locale('ar')),
        'shadows': () => profile(shadows: true),
      }.entries) {
        expect(
          mismatch.value,
          throwsA(
            isA<TestFailure>().having(
              (failure) => failure.message,
              'message',
              allOf(
                contains('CAPTURE PROFILE MISMATCH'),
                contains(mismatch.key),
              ),
            ),
          ),
          reason: mismatch.key,
        );
      }
    });
  });
}
