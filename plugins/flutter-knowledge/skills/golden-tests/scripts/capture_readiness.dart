import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

class FontCoverage {
  FontCoverage._(
    this._data,
    this._tables,
    this.weight,
    this.italic,
    this.variable,
  );

  final ByteData _data;
  final List<_Cmap> _tables;
  final int? weight;
  final bool italic;
  final bool variable;

  static FontCoverage? parse(Uint8List bytes) {
    if (bytes.length < 12) return null;
    final data = ByteData.sublistView(bytes);
    final magic = data.getUint32(0);
    if (magic != 0x00010000 && magic != 0x4F54544F && magic != 0x74727565) {
      return null;
    }
    final cmapOffset = _table(data, 'cmap');
    if (cmapOffset == null || cmapOffset + 4 > data.lengthInBytes) return null;
    final tables = <_Cmap>[];
    final count = data.getUint16(cmapOffset + 2);
    for (var i = 0; i < count; i++) {
      final record = cmapOffset + 4 + i * 8;
      if (record + 8 > data.lengthInBytes) break;
      final platform = data.getUint16(record);
      final encoding = data.getUint16(record + 2);
      final supported =
          platform == 0 || (platform == 3 && (encoding == 1 || encoding == 10));
      if (!supported) continue;
      final offset = cmapOffset + data.getUint32(record + 4);
      if (offset + 16 > data.lengthInBytes) continue;
      final format = data.getUint16(offset);
      if (format == 4 || format == 12) tables.add(_Cmap(format, offset));
    }
    if (tables.isEmpty) return null;
    final os2 = _table(data, 'OS/2');
    int? weight;
    var italic = false;
    if (os2 != null && os2 + 64 <= data.lengthInBytes) {
      weight = data.getUint16(os2 + 4);
      italic = data.getUint16(os2 + 62) & 1 == 1;
    }
    return FontCoverage._(
      data,
      tables,
      weight,
      italic,
      _table(data, 'fvar') != null,
    );
  }

  static int? _table(ByteData data, String name) {
    final count = data.getUint16(4);
    for (var i = 0; i < count; i++) {
      final record = 12 + i * 16;
      if (record + 16 > data.lengthInBytes) return null;
      final tag = String.fromCharCodes([
        for (var k = 0; k < 4; k++) data.getUint8(record + k),
      ]);
      if (tag == name) return data.getUint32(record + 8);
    }
    return null;
  }

  bool covers(int codePoint) {
    for (final table in _tables) {
      final found = table.format == 4
          ? _format4(table.offset, codePoint)
          : _format12(table.offset, codePoint);
      if (found) return true;
    }
    return false;
  }

  bool _format4(int sub, int codePoint) {
    if (codePoint > 0xFFFF) return false;
    final data = _data;
    final segments = data.getUint16(sub + 6) ~/ 2;
    final ends = sub + 14;
    final starts = ends + 2 * segments + 2;
    final deltas = starts + 2 * segments;
    final ranges = deltas + 2 * segments;
    if (ranges + 2 * segments > data.lengthInBytes) return false;
    var low = 0;
    var high = segments - 1;
    while (low < high) {
      final mid = (low + high) ~/ 2;
      if (data.getUint16(ends + 2 * mid) < codePoint) {
        low = mid + 1;
      } else {
        high = mid;
      }
    }
    if (low >= segments) return false;
    final start = data.getUint16(starts + 2 * low);
    if (data.getUint16(ends + 2 * low) < codePoint || start > codePoint) {
      return false;
    }
    final delta = data.getUint16(deltas + 2 * low);
    final rangeAddress = ranges + 2 * low;
    final range = data.getUint16(rangeAddress);
    if (range == 0) return ((codePoint + delta) & 0xFFFF) != 0;
    final glyphAddress = rangeAddress + range + 2 * (codePoint - start);
    if (glyphAddress + 2 > data.lengthInBytes) return false;
    final glyph = data.getUint16(glyphAddress);
    return glyph != 0 && ((glyph + delta) & 0xFFFF) != 0;
  }

  bool _format12(int sub, int codePoint) {
    final data = _data;
    final groups = data.getUint32(sub + 12);
    final base = sub + 16;
    if (base + groups * 12 > data.lengthInBytes) return false;
    var low = 0;
    var high = groups - 1;
    while (low <= high) {
      final mid = (low + high) ~/ 2;
      final record = base + mid * 12;
      final start = data.getUint32(record);
      final end = data.getUint32(record + 4);
      if (codePoint < start) {
        high = mid - 1;
      } else if (codePoint > end) {
        low = mid + 1;
      } else {
        return data.getUint32(record + 8) + codePoint - start != 0;
      }
    }
    return false;
  }
}

class _Cmap {
  const _Cmap(this.format, this.offset);
  final int format;
  final int offset;
}

class CaptureFontFace {
  const CaptureFontFace({
    required this.family,
    required this.source,
    required this.coverage,
  });

  final String family;
  final String source;
  final FontCoverage? coverage;
}

class CaptureFontFile {
  const CaptureFontFile(this.family, this.path);
  final String family;
  final String path;
}

class CaptureFonts {
  CaptureFonts._(this._faces, this.standIn, this.sdkFontDirectory);

  final Map<String, List<CaptureFontFace>> _faces;
  final String? standIn;
  final String? sdkFontDirectory;
  final Set<String> repairs = {};

  Iterable<String> get families => _faces.keys;

  bool hasFamily(String family) => _faces.containsKey(family);

  List<CaptureFontFace> facesOf(String family) => _faces[family] ?? const [];

  Map<String, dynamic> toJson() => {
    'standIn': standIn,
    'sdkFontDirectory': sdkFontDirectory,
    'families': {
      for (final entry in _faces.entries)
        entry.key: [
          for (final face in entry.value)
            {
              'source': face.source,
              'weight': face.coverage?.weight,
              'italic': face.coverage?.italic,
              'coverageReadable': face.coverage != null,
            },
        ],
    },
    'repairs': repairs.toList()..sort(),
  };
}

String? captureSdkFontDirectory() {
  final root = Platform.environment['FLUTTER_ROOT'];
  if (root != null && root.isNotEmpty) {
    final directory = '$root/bin/cache/artifacts/material_fonts';
    if (Directory(directory).existsSync()) return directory;
  }
  final configFile = File('.dart_tool/package_config.json');
  if (!configFile.existsSync()) return null;
  final config = json.decode(configFile.readAsStringSync()) as Map;
  for (final package in config['packages'] as List) {
    if (package['name'] == 'flutter') {
      final root = configFile.absolute.uri
          .resolve(package['rootUri'] as String)
          .resolve('../../');
      final directory =
          '${root.toFilePath()}bin/cache/artifacts/material_fonts';
      if (Directory(directory).existsSync()) return directory;
    }
  }
  return null;
}

Future<CaptureFonts> loadCaptureFonts({
  String standIn = 'Roboto',
  List<CaptureFontFile> files = const [],
}) async {
  final pending = <String, List<MapEntry<String, Uint8List>>>{};
  void add(String family, String source, Uint8List bytes) =>
      pending.putIfAbsent(family, () => []).add(MapEntry(source, bytes));

  final manifest =
      json.decode(await rootBundle.loadString('FontManifest.json')) as List;
  for (final family in manifest.cast<Map<String, dynamic>>()) {
    for (final font in (family['fonts'] as List).cast<Map<String, dynamic>>()) {
      final asset = font['asset'] as String;
      final data = await rootBundle.load(asset);
      add(
        family['family'] as String,
        'asset:$asset',
        data.buffer.asUint8List(data.offsetInBytes, data.lengthInBytes),
      );
    }
  }
  final sdk = captureSdkFontDirectory();
  if (sdk != null) {
    final wanted = <String, List<String>>{
      'Roboto': [
        for (final weight in const [
          'Thin',
          'Light',
          'Regular',
          'Medium',
          'Bold',
          'Black',
        ])
          'Roboto-$weight.ttf',
      ],
      'MaterialIcons': ['MaterialIcons-Regular.otf'],
    };
    for (final entry in wanted.entries) {
      if (pending.containsKey(entry.key)) continue;
      for (final name in entry.value) {
        final file = File('$sdk/$name');
        if (file.existsSync()) {
          add(entry.key, 'sdk:$name', file.readAsBytesSync());
        }
      }
    }
  }
  for (final file in files) {
    add(file.family, 'file:${file.path}', File(file.path).readAsBytesSync());
  }

  final faces = <String, List<CaptureFontFace>>{};
  for (final entry in pending.entries) {
    final loader = FontLoader(entry.key);
    for (final font in entry.value) {
      loader.addFont(Future.value(ByteData.sublistView(font.value)));
    }
    await loader.load();
    faces[entry.key] = [
      for (final font in entry.value)
        CaptureFontFace(
          family: entry.key,
          source: font.key,
          coverage: FontCoverage.parse(font.value),
        ),
    ];
  }
  return CaptureFonts._(
    faces,
    faces.containsKey(standIn) ? standIn : null,
    sdk,
  );
}

TextStyle? _fill(CaptureFonts fonts, String slot, TextStyle? style) {
  final family = fonts.standIn;
  if (style == null || family == null) return style;
  if (style is WidgetStateTextStyle) {
    return WidgetStateTextStyle.resolveWith(
      (states) =>
          _fill(fonts, slot, style.resolve(states)) ?? const TextStyle(),
    );
  }
  if (style.fontFamily != null) return style;
  fonts.repairs.add(slot);
  return style.copyWith(fontFamily: family);
}

WidgetStateProperty<TextStyle?>? _fillState(
  CaptureFonts fonts,
  String slot,
  WidgetStateProperty<TextStyle?>? property,
) {
  if (property == null) return null;
  return WidgetStateProperty.resolveWith(
    (states) => _fill(fonts, slot, property.resolve(states)),
  );
}

TextTheme _fillTextTheme(CaptureFonts fonts, String slot, TextTheme theme) {
  TextStyle? fill(String name, TextStyle? style) =>
      _fill(fonts, '$slot.$name', style);
  return theme.copyWith(
    displayLarge: fill('displayLarge', theme.displayLarge),
    displayMedium: fill('displayMedium', theme.displayMedium),
    displaySmall: fill('displaySmall', theme.displaySmall),
    headlineLarge: fill('headlineLarge', theme.headlineLarge),
    headlineMedium: fill('headlineMedium', theme.headlineMedium),
    headlineSmall: fill('headlineSmall', theme.headlineSmall),
    titleLarge: fill('titleLarge', theme.titleLarge),
    titleMedium: fill('titleMedium', theme.titleMedium),
    titleSmall: fill('titleSmall', theme.titleSmall),
    bodyLarge: fill('bodyLarge', theme.bodyLarge),
    bodyMedium: fill('bodyMedium', theme.bodyMedium),
    bodySmall: fill('bodySmall', theme.bodySmall),
    labelLarge: fill('labelLarge', theme.labelLarge),
    labelMedium: fill('labelMedium', theme.labelMedium),
    labelSmall: fill('labelSmall', theme.labelSmall),
  );
}

ThemeData captureTheme(ThemeData theme, CaptureFonts fonts) {
  TextStyle? fill(String slot, TextStyle? style) => _fill(fonts, slot, style);
  return theme.copyWith(
    textTheme: _fillTextTheme(fonts, 'textTheme', theme.textTheme),
    primaryTextTheme: _fillTextTheme(
      fonts,
      'primaryTextTheme',
      theme.primaryTextTheme,
    ),
    appBarTheme: theme.appBarTheme.copyWith(
      titleTextStyle: fill(
        'appBarTheme.titleTextStyle',
        theme.appBarTheme.titleTextStyle,
      ),
      toolbarTextStyle: fill(
        'appBarTheme.toolbarTextStyle',
        theme.appBarTheme.toolbarTextStyle,
      ),
    ),
    snackBarTheme: theme.snackBarTheme.copyWith(
      contentTextStyle: fill(
        'snackBarTheme.contentTextStyle',
        theme.snackBarTheme.contentTextStyle,
      ),
    ),
    dialogTheme: theme.dialogTheme.copyWith(
      titleTextStyle: fill(
        'dialogTheme.titleTextStyle',
        theme.dialogTheme.titleTextStyle,
      ),
      contentTextStyle: fill(
        'dialogTheme.contentTextStyle',
        theme.dialogTheme.contentTextStyle,
      ),
    ),
    tooltipTheme: theme.tooltipTheme.copyWith(
      textStyle: fill('tooltipTheme.textStyle', theme.tooltipTheme.textStyle),
    ),
    listTileTheme: theme.listTileTheme.copyWith(
      titleTextStyle: fill(
        'listTileTheme.titleTextStyle',
        theme.listTileTheme.titleTextStyle,
      ),
      subtitleTextStyle: fill(
        'listTileTheme.subtitleTextStyle',
        theme.listTileTheme.subtitleTextStyle,
      ),
      leadingAndTrailingTextStyle: fill(
        'listTileTheme.leadingAndTrailingTextStyle',
        theme.listTileTheme.leadingAndTrailingTextStyle,
      ),
    ),
    tabBarTheme: theme.tabBarTheme.copyWith(
      labelStyle: fill('tabBarTheme.labelStyle', theme.tabBarTheme.labelStyle),
      unselectedLabelStyle: fill(
        'tabBarTheme.unselectedLabelStyle',
        theme.tabBarTheme.unselectedLabelStyle,
      ),
    ),
    bottomNavigationBarTheme: theme.bottomNavigationBarTheme.copyWith(
      selectedLabelStyle: fill(
        'bottomNavigationBarTheme.selectedLabelStyle',
        theme.bottomNavigationBarTheme.selectedLabelStyle,
      ),
      unselectedLabelStyle: fill(
        'bottomNavigationBarTheme.unselectedLabelStyle',
        theme.bottomNavigationBarTheme.unselectedLabelStyle,
      ),
    ),
    chipTheme: theme.chipTheme.copyWith(
      labelStyle: fill('chipTheme.labelStyle', theme.chipTheme.labelStyle),
    ),
    textButtonTheme: TextButtonThemeData(
      style: _withState(fonts, 'textButtonTheme', theme.textButtonTheme.style),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: _withState(
        fonts,
        'filledButtonTheme',
        theme.filledButtonTheme.style,
      ),
    ),
    elevatedButtonTheme: ElevatedButtonThemeData(
      style: _withState(
        fonts,
        'elevatedButtonTheme',
        theme.elevatedButtonTheme.style,
      ),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: _withState(
        fonts,
        'outlinedButtonTheme',
        theme.outlinedButtonTheme.style,
      ),
    ),
  );
}

ButtonStyle? _withState(CaptureFonts fonts, String slot, ButtonStyle? style) {
  if (style == null) return null;
  return style.copyWith(
    textStyle: _fillState(fonts, '$slot.textStyle', style.textStyle),
  );
}

class CaptureThemeScope extends StatelessWidget {
  const CaptureThemeScope({
    super.key,
    required this.fonts,
    required this.child,
  });

  final CaptureFonts fonts;
  final Widget child;

  @override
  Widget build(BuildContext context) =>
      Theme(data: captureTheme(Theme.of(context), fonts), child: child);
}

class ReadinessFinding {
  const ReadinessFinding({
    required this.kind,
    required this.blocking,
    required this.detail,
    required this.where,
  });

  final String kind;
  final bool blocking;
  final String detail;
  final String where;

  Map<String, dynamic> toJson() => {
    'kind': kind,
    'blocking': blocking,
    'detail': detail,
    'where': where,
  };
}

class CaptureReadiness {
  CaptureReadiness(this.findings, this.textRuns, this.familiesUsed, this.fonts);

  final List<ReadinessFinding> findings;
  final int textRuns;
  final Set<String> familiesUsed;
  final CaptureFonts fonts;

  Iterable<ReadinessFinding> get blockers => findings.where((f) => f.blocking);

  Iterable<ReadinessFinding> get warnings => findings.where((f) => !f.blocking);

  bool get ready => blockers.isEmpty;

  String get status => ready ? 'READY' : 'BLOCKED';

  Map<String, dynamic> toJson() => {
    'status': status,
    'textRuns': textRuns,
    'familiesUsed': familiesUsed.toList()..sort(),
    'findings': [for (final finding in findings) finding.toJson()],
    'fonts': fonts.toJson(),
  };

  String describe() {
    final lines = [
      'CAPTURE READINESS $status: ${blockers.length} blocker(s), '
          '${warnings.length} warning(s), $textRuns text run(s) inspected',
    ];
    for (final finding in findings) {
      lines.add(
        '  ${finding.blocking ? 'BLOCKER' : 'warning'} ${finding.kind}: '
        '${finding.detail} [${finding.where}]',
      );
    }
    return lines.join('\n');
  }
}

bool _ignorable(int c) =>
    c <= 0x20 ||
    (c >= 0x7f && c <= 0xa0) ||
    c == 0xad ||
    (c >= 0x200b && c <= 0x200f) ||
    (c >= 0x202a && c <= 0x202e) ||
    (c >= 0x2060 && c <= 0x2064) ||
    (c >= 0x2066 && c <= 0x2069) ||
    c == 0xfeff;

String _hex(int c) => 'U+${c.toRadixString(16).toUpperCase().padLeft(4, '0')}';

String _where(RenderObject object) {
  final creator = object.debugCreator;
  if (creator is DebugCreator) {
    return creator.element.debugGetCreatorChain(4);
  }
  return object.runtimeType.toString();
}

void _walkRender(RenderObject object, void Function(RenderObject) visit) {
  if (object is RenderOffstage && object.offstage) return;
  visit(object);
  object.visitChildren((child) => _walkRender(child, visit));
}

void _walkSpan(
  InlineSpan span,
  TextStyle? inherited,
  void Function(String text, TextStyle? style) visit,
) {
  if (span is! TextSpan) return;
  final style = inherited == null || span.style == null
      ? span.style ?? inherited
      : inherited.merge(span.style);
  final text = span.text;
  if (text != null && text.isNotEmpty) visit(text, style);
  for (final child in span.children ?? const <InlineSpan>[]) {
    _walkSpan(child, style, visit);
  }
}

CaptureReadiness inspectCapture(
  WidgetTester tester,
  CaptureFonts fonts, {
  Finder? within,
  bool requireText = true,
}) {
  final findings = <String, ReadinessFinding>{};
  final used = <String>{};
  var runs = 0;
  void report(String kind, bool blocking, String detail, String where) {
    findings.putIfAbsent(
      '$kind|$detail',
      () => ReadinessFinding(
        kind: kind,
        blocking: blocking,
        detail: detail,
        where: where,
      ),
    );
  }

  void inspectText(InlineSpan? text, RenderObject object) {
    if (text == null) return;
    _walkSpan(text, null, (value, style) {
      runs++;
      final primary = style?.fontFamily;
      final sample = value.length > 24 ? '${value.substring(0, 24)}…' : value;
      if (primary == null) {
        report(
          'defaultFamily',
          true,
          'text "$sample" has no effective font family; flutter test draws it '
              'with the Ahem test font',
          _where(object),
        );
        return;
      }
      used.add(primary);
      final chain = [primary, ...?style?.fontFamilyFallback];
      final loaded = chain.where(fonts.hasFamily).toList();
      if (!fonts.hasFamily(primary)) {
        report(
          'unloadedFamily',
          true,
          'family "$primary" used by "$sample" is not loaded',
          _where(object),
        );
      }
      for (final family in chain.skip(1).where((f) => !fonts.hasFamily(f))) {
        report(
          'unloadedFallback',
          false,
          'fallback family "$family" is not loaded',
          _where(object),
        );
      }
      if (loaded.isEmpty) return;
      final faces = [for (final family in loaded) ...fonts.facesOf(family)];
      final unreadable = faces.where((face) => face.coverage == null).toList();
      if (unreadable.isNotEmpty) {
        report(
          'unverifiableCoverage',
          true,
          'font ${unreadable.first.source} (${unreadable.first.family}) has no '
              'readable cmap; glyph support cannot be shown',
          _where(object),
        );
        return;
      }
      final missing = <int>{};
      for (final c in value.runes) {
        if (_ignorable(c)) continue;
        if (!faces.any((face) => face.coverage!.covers(c))) missing.add(c);
      }
      if (missing.isNotEmpty) {
        final shown = missing.take(8).map(_hex).join(' ');
        report(
          'missingGlyph',
          true,
          'no loaded font in [${loaded.join(', ')}] covers $shown'
              '${missing.length > 8 ? ' and ${missing.length - 8} more' : ''} '
              'in "$sample"',
          _where(object),
        );
      }
      if (fonts.hasFamily(primary)) {
        final own = fonts.facesOf(primary);
        final variable = own.any((face) => face.coverage?.variable ?? false);
        final requested = style?.fontWeight?.value ?? 400;
        final weights = {
          for (final face in own)
            if (face.coverage?.weight != null) face.coverage!.weight!,
        };
        if (!variable && weights.isNotEmpty && !weights.contains(requested)) {
          report(
            'weightNotProvided',
            false,
            'family "$primary" has weights ${(weights.toList()..sort()).join('/')} '
                'but "$sample" requests $requested',
            _where(object),
          );
        }
        if (style?.fontStyle == FontStyle.italic &&
            !own.any((face) => face.coverage?.italic ?? false)) {
          report(
            'italicNotProvided',
            false,
            'family "$primary" has no italic face for "$sample"',
            _where(object),
          );
        }
      }
    });
  }

  final roots = within == null
      ? [for (final view in tester.binding.renderViews) view as RenderObject]
      : [for (final element in within.evaluate()) element.renderObject!];
  for (final root in roots) {
    _walkRender(root, (object) {
      if (object is RenderParagraph) inspectText(object.text, object);
      if (object is RenderEditable) inspectText(object.text, object);
    });
  }
  if (requireText && runs == 0) {
    report(
      'noText',
      true,
      'no rendered text was found, so no font support was inspected',
      'capture root',
    );
  }
  return CaptureReadiness(findings.values.toList(), runs, used, fonts);
}

CaptureReadiness expectCaptureReady(
  WidgetTester tester,
  CaptureFonts fonts, {
  Finder? within,
  bool requireText = true,
  String? reportPath,
}) {
  final readiness = inspectCapture(
    tester,
    fonts,
    within: within,
    requireText: requireText,
  );
  if (reportPath != null) {
    final file = File(reportPath)..parent.createSync(recursive: true);
    file.writeAsStringSync(
      const JsonEncoder.withIndent('  ').convert(readiness.toJson()),
    );
  }
  if (!readiness.ready) throw TestFailure(readiness.describe());
  return readiness;
}

void expectCaptureProfile(
  BuildContext context, {
  required Size viewport,
  required double devicePixelRatio,
  required Locale locale,
  required double textScale,
  EdgeInsets safeArea = EdgeInsets.zero,
  double keyboardInset = 0,
  bool shadows = true,
}) {
  bool near(double a, double b) => (a - b).abs() < 1e-6;
  final mismatches = <String>[];
  void check(String name, Object expected, Object observed, bool same) {
    if (!same) mismatches.add('$name: expected $expected, observed $observed');
  }

  final size = MediaQuery.sizeOf(context);
  final dpr = MediaQuery.devicePixelRatioOf(context);
  final padding = MediaQuery.paddingOf(context);
  final scale = MediaQuery.textScalerOf(context).scale(1);
  final keyboard = MediaQuery.viewInsetsOf(context).bottom;
  final actualLocale = Localizations.localeOf(context);
  check(
    'viewport',
    viewport,
    size,
    near(size.width, viewport.width) && near(size.height, viewport.height),
  );
  check('devicePixelRatio', devicePixelRatio, dpr, near(dpr, devicePixelRatio));
  check(
    'safeArea',
    safeArea,
    padding,
    near(padding.top, safeArea.top) &&
        near(padding.bottom, safeArea.bottom) &&
        near(padding.left, safeArea.left) &&
        near(padding.right, safeArea.right),
  );
  check('textScale', textScale, scale, near(scale, textScale));
  check(
    'keyboardInset',
    keyboardInset,
    keyboard,
    near(keyboard, keyboardInset),
  );
  check('locale', locale, actualLocale, actualLocale == locale);
  check(
    'shadows',
    shadows,
    !debugDisableShadows,
    shadows == !debugDisableShadows,
  );
  if (mismatches.isNotEmpty) {
    throw TestFailure('CAPTURE PROFILE MISMATCH\n  ${mismatches.join('\n  ')}');
  }
}
