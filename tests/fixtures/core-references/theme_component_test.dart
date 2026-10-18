import 'package:core_reference_check/core/theme/app_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter/rendering.dart';
import 'package:flutter_test/flutter_test.dart';

final roles = [
  FixtureRoles(
    name: 'light',
    brightness: Brightness.light,
    colors: List.generate(7, (index) => Color(0xff103040 + index * 0x10101)),
  ),
  FixtureRoles(
    name: 'dark',
    brightness: Brightness.dark,
    colors: List.generate(7, (index) => Color(0xff90a0b0 + index * 0x10101)),
  ),
  FixtureRoles(
    name: 'custom overrides',
    brightness: Brightness.light,
    colors: List.generate(7, (index) => Color(0xffc02060 + index * 0x10101)),
  ),
];

void main() {
  for (final skin in roles) {
    for (final state in ['enabled', 'disabled', 'loading']) {
      testWidgets(
        '${skin.name}: $state buttons render component fill and ink',
        (tester) async {
          final isEnabled = state == 'enabled';
          final theme = FixtureTheme.of(skin);
          await tester.pumpWidget(
            MaterialApp(
              theme: theme,
              home: Scaffold(
                body: Column(
                  children: [
                    FilledButton(
                      key: const ValueKey('material'),
                      onPressed: isEnabled ? () {} : null,
                      child: const Text('Material label'),
                    ),
                    FixturePrimaryButton(
                      key: const ValueKey('core'),
                      onPressed: state == 'disabled' ? null : () {},
                      isLoading: state == 'loading',
                    ),
                  ],
                ),
              ),
            ),
          );

          for (final key in ['material', 'core']) {
            final button = find.byKey(ValueKey(key));
            final material = tester.widget<Material>(
              find.descendant(of: button, matching: find.byType(Material)),
            );
            final label = tester.renderObject<RenderParagraph>(
              find.descendant(of: button, matching: find.byType(RichText)),
            );
            expect(
              material.color,
              isEnabled ? skin.buttonBackground : skin.buttonDisabledBackground,
            );
            expect(
              label.text.style!.color,
              isEnabled ? skin.buttonText : skin.buttonDisabledText,
            );
            expect(
              label.text.style!.fontSize,
              FixtureTheme.buttonText.fontSize,
            );
            expect(
              label.text.style!.fontWeight,
              FixtureTheme.buttonText.fontWeight,
            );
            expect(material.shape, FixtureTheme.buttonShape);
            expect(
              tester.getSize(button).width,
              greaterThanOrEqualTo(FixtureTheme.buttonMinimumSize.width),
            );
            expect(
              tester.getSize(button).height,
              greaterThanOrEqualTo(FixtureTheme.buttonMinimumSize.height),
            );
          }
          final style = theme.filledButtonTheme.style!;
          expect(style.padding!.resolve({}), FixtureTheme.buttonPadding);
          expect(style.animationDuration, FixtureTheme.buttonAnimation);
        },
      );
    }

    testWidgets(
      '${skin.name}: field paints ordinary and focused role borders',
      (tester) async {
        final focusNode = FocusNode();
        addTearDown(focusNode.dispose);
        final theme = FixtureTheme.of(skin);
        await tester.pumpWidget(
          MaterialApp(
            theme: theme,
            home: Scaffold(body: TextField(focusNode: focusNode)),
          ),
        );

        final border = find.descendant(
          of: find.byType(TextField),
          matching: find.byType(CustomPaint),
        );
        expect(
          tester.renderObject(border),
          paints..rrect(color: skin.textFieldBorder, strokeWidth: 3),
        );
        focusNode.requestFocus();
        await tester.pumpAndSettle();
        expect(
          tester.renderObject(border),
          paints..rrect(color: skin.textFieldFocusedBorder, strokeWidth: 5),
        );
        focusNode.unfocus();
        await tester.pumpAndSettle();
        expect(
          tester.renderObject(border),
          paints..rrect(color: skin.textFieldBorder, strokeWidth: 3),
        );

        final decoration = theme.inputDecorationTheme;
        for (final borders in [
          (decoration.enabledBorder, FixtureTheme.inputEnabledBorder),
          (decoration.focusedBorder, FixtureTheme.inputFocusedBorder),
        ]) {
          final actual = borders.$1! as OutlineInputBorder;
          final original = borders.$2;
          expect(actual.borderRadius, original.borderRadius);
          expect(actual.gapPadding, original.gapPadding);
          expect(actual.borderSide.style, original.borderSide.style);
        }
        expect(decoration.contentPadding, FixtureTheme.inputPadding);
        expect(decoration.disabledBorder, FixtureTheme.inputDisabledBorder);
        expect(decoration.errorBorder, FixtureTheme.inputErrorBorder);
        expect(decoration.floatingLabelBehavior, FloatingLabelBehavior.always);
      },
    );
  }
}
