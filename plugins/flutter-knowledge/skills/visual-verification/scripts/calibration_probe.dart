import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';

Map<String, double> calibrationBounds(RenderBox box) {
  final origin = box.localToGlobal(Offset.zero);
  return {
    'x': origin.dx,
    'y': origin.dy,
    'width': box.size.width,
    'height': box.size.height,
  };
}

Map<String, Object?> calibrationTypography(RenderParagraph paragraph) {
  final span = paragraph.text;
  if (span is! TextSpan || span.children?.isNotEmpty == true) {
    throw UnsupportedError('Export each effective rich-text run separately');
  }
  final style = span.style!;
  final fontSize = style.fontSize!;
  return {
    'text': span.text,
    'font_family': style.fontFamily,
    'font_weight': style.fontWeight?.value,
    'font_size': fontSize,
    'letter_spacing': style.letterSpacing ?? 0,
    'line_height': style.height == null ? null : fontSize * style.height!,
    'scaled_font_size': paragraph.textScaler.scale(fontSize),
    'bounds': calibrationBounds(paragraph),
  };
}

Map<String, Object?> calibrationField(WidgetTester tester, Finder field) {
  final editable = find.descendant(
    of: field,
    matching: find.byType(EditableText),
  );
  expect(editable, findsOneWidget);
  final container = InputDecorator.containerOf(tester.element(editable));
  if (container == null) {
    throw UnsupportedError(
      'This field has no InputDecorator painted container',
    );
  }
  return {
    'outer_bounds': calibrationBounds(tester.renderObject<RenderBox>(field)),
    'painted_bounds': calibrationBounds(container),
  };
}

Map<String, Object?> calibrationViewport(BuildContext context) {
  final media = MediaQuery.of(context);
  return {
    'width': media.size.width,
    'height': media.size.height,
    'dpr': media.devicePixelRatio,
    'locale': Localizations.localeOf(context).toLanguageTag(),
    'safe_area': {
      'top': media.padding.top,
      'right': media.padding.right,
      'bottom': media.padding.bottom,
      'left': media.padding.left,
    },
    'text_scale': media.textScaler.scale(16) / 16,
  };
}

Map<String, String> calibrationBinding(String path) {
  final file = File(path).absolute;
  final hashed = Process.runSync('python3', [
    '-c',
    'import hashlib, pathlib, sys; print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())',
    file.path,
  ]);
  if (hashed.exitCode != 0) {
    throw StateError('Cannot bind runtime input: ${hashed.stderr}');
  }
  return {'path': file.path, 'sha256': (hashed.stdout as String).trim()};
}

void writeCalibrationExport(
  String path,
  List<String> inputs,
  Map<String, Object?> rows,
) {
  final expanded =
      inputs
          .expand((path) {
            if (Directory(path).existsSync()) {
              return Directory(path)
                  .listSync(recursive: true)
                  .whereType<File>()
                  .map((file) => file.path);
            }
            return [path];
          })
          .toSet()
          .toList()
        ..sort();
  File(path).writeAsStringSync(
    jsonEncode({
      'bindings': expanded.map(calibrationBinding).toList(),
      'rows': rows,
    }),
  );
}
