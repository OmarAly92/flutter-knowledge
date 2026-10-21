import 'package:flutter/material.dart';

sealed class CaptureFixtureFonts {
  static const String? text = null;
}

@immutable
class CaptureFixtureTypography {
  const CaptureFixtureTypography();

  TextStyle _style(double size, FontWeight weight) => TextStyle(
    fontSize: size,
    fontWeight: weight,
    height: 1.5,
    fontFamily: CaptureFixtureFonts.text,
  );

  TextStyle get headingSm => _style(22, FontWeight.w700);
  TextStyle get bodyMd => _style(16, FontWeight.w400);
}

@immutable
class CaptureFixtureTokens extends ThemeExtension<CaptureFixtureTokens> {
  const CaptureFixtureTokens({this.text = const CaptureFixtureTypography()});

  final CaptureFixtureTypography text;

  @override
  CaptureFixtureTokens copyWith({CaptureFixtureTypography? text}) =>
      CaptureFixtureTokens(text: text ?? this.text);

  @override
  CaptureFixtureTokens lerp(covariant CaptureFixtureTokens? other, double t) =>
      this;
}

extension CaptureFixtureContext on BuildContext {
  CaptureFixtureTokens get tokens =>
      Theme.of(this).extension<CaptureFixtureTokens>()!;
}

sealed class CaptureFixtureTheme {
  static ThemeData get light {
    const tokens = CaptureFixtureTokens();
    return ThemeData(
      useMaterial3: true,
      fontFamily: CaptureFixtureFonts.text,
      extensions: const [tokens],
      appBarTheme: AppBarTheme(
        titleTextStyle: tokens.text.headingSm.copyWith(color: Colors.black),
      ),
      snackBarTheme: SnackBarThemeData(
        contentTextStyle: tokens.text.bodyMd.copyWith(color: Colors.white),
      ),
    );
  }
}

class CaptureFixtureText extends StatelessWidget {
  const CaptureFixtureText(this.data, {super.key});

  final String data;

  @override
  Widget build(BuildContext context) => Text(
    data,
    style: context.tokens.text.bodyMd.copyWith(color: Colors.black),
  );
}

class CaptureFixtureAppbar extends StatelessWidget
    implements PreferredSizeWidget {
  const CaptureFixtureAppbar({super.key, required this.titleText});

  final String titleText;

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) =>
      AppBar(title: CaptureFixtureText(titleText));
}
