#!/usr/bin/env python3
"""Build the benchmark fixture projects in the 2.0.0 shape the skills teach: design tokens read as
`context.tokens` from lib/core/theme/, per-feature `<feature>_injection.dart` files wired through
lib/app_injection.dart, the router library in lib/core/router/, l10n in lib/core/l10n/, and the data
core in lib/core/data/. Each project also carries legacy code that breaks the rules on purpose,
as traps for "legacy never overrides": an `orders` feature on Bloc with untyped DI registrations,
`RoutesStrings._()`, and (drift) a `budget` feature whose params return a drift Companion and whose
data source core registers.

Usage: build_fixtures.py <out_dir>
  -> <out_dir>/fixture-drift, fixture-hive: the core plus the legacy features, for d1-d4, h1, h2.
  -> <out_dir>/fixture-app: the drift project plus a `trips` feature that follows the skills, email
     and phone validators, a legacy mockito test, and design/prototype.html (from make_prototype.py).
     No AppMotion. Tasks f1, f2, t1, g1, m2.
  -> <out_dir>/fixture-skin: the app project with a full skin layer (SkinRegistry with a JSON skin,
     SkinCubit persisted through CacheHelper) and an AppMotion token group. Tasks s1, s2, m1.
  -> <out_dir>/fixture-older: the app project on the pre-2.0 theme (a flat AppColors and a static
     AppTextStyle, no AppTokens), to test the skills' older-project notes. Task o1.
  Each also gets a -nowrap copy with PrimaryButton, AppTextField, AppLoader and AppErrorWidget removed.
"""
import os, re, shutil, sys, textwrap

OUT = sys.argv[1] if __name__ == '__main__' else None
NOWRAP_REMOVED = ('buttons/primary_button', 'inputs/app_text_field', 'feedback/app_loader', 'feedback/app_error_widget')


def w(root, path, text):
    p = os.path.join(root, path)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write(textwrap.dedent(text).lstrip('\n'))


EN = '''{
  "orders": "Orders",
  "retry": "Retry",
  "save": "Save",
  "somethingWentWrong": "Something went wrong",
  "fieldIsRequired": "This field is required",
  "noInternetConnection": "No internet connection",
  "themeLight": "Light",
  "themeDark": "Dark"
}
'''
AR = '''{
  "orders": "الطلبات",
  "retry": "إعادة المحاولة",
  "save": "حفظ",
  "somethingWentWrong": "حدث خطأ ما",
  "fieldIsRequired": "هذا الحقل مطلوب",
  "noInternetConnection": "لا يوجد اتصال بالإنترنت",
  "themeLight": "فاتح",
  "themeDark": "داكن"
}
'''


def locale_keys(keys):
    return ('// DO NOT EDIT. This is code generated via package:easy_localization/generate.dart\n\n'
            'abstract class LocaleKeys {\n'
            + ''.join("  static const %s = '%s';\n" % (k, k) for k in keys)
            + '}\n')


BASE_KEYS = ['orders', 'retry', 'save', 'somethingWentWrong', 'fieldIsRequired', 'noInternetConnection',
             'themeLight', 'themeDark']

# ---------- the skin contract: base slots are abstract, derived slots have a default ----------
APP_SKIN_SLOTS = '''
  /// The base color of every screen, painted by [AppScaffold] behind all
  /// content. Example: the page behind the trips list.
  Color get background;

  /// The color of blocks sitting on top of [background]. Example: the
  /// card holding one trip in the trips list.
  Color get surface;

  /// A sunken variant of [surface] for blocks that blend with the page.
  /// Example: the tinted fill behind an empty-state illustration.
  Color get card;

  /// The default outline around cards and inputs. Example: the stroke
  /// around a trip card.
  Color get border;

  /// The brand blue used for primary actions and emphasis. Example: the
  /// Save button and the trip price.
  Color get primary;

  /// A readable shade of [primary] for text on [primaryLight] fills.
  /// Example: a label inside a soft brand pill.
  Color get primaryDark;

  /// A soft tint of [primary] used behind brand content. Example: the fill
  /// of a soft brand pill.
  Color get primaryLight;

  /// The sky-blue secondary color for highlights that must not read as
  /// primary. Example: an informational icon on a trip.
  Color get accent;

  /// A soft tint of [accent] used behind accent content. Example: the
  /// square behind an informational icon.
  Color get accentLight;

  /// The strongest text color, for titles. Example: a trip's title.
  Color get textPrimary;

  /// The medium-emphasis text color. Example: a trip's destination.
  Color get textSecondary;

  /// The lowest-emphasis text color, for fine print. Example: a
  /// timestamp under a trip.
  Color get textMuted;

  /// The text color on top of [primary] fills. Example: the Save label.
  Color get textOnPrimary;

  /// The color of a positive outcome. Example: the success snackbar.
  Color get success;

  /// A soft tint of [success] used as a background. Example: the fill of
  /// a confirmed badge.
  Color get successLight;

  /// The color of a failure or destructive state. Example: the error
  /// snackbar.
  Color get error;

  /// A soft tint of [error] used as a background. Example: the fill behind
  /// a destructive action's icon.
  Color get errorLight;

  /// The color of caution. Example: a trip that needs attention.
  Color get warning;

  /// A soft tint of [warning] used as a background. Example: the fill
  /// behind a caution badge.
  Color get warningLight;

  /// The fill of the top app bar. Example: the bar behind 'Trips'.
  Color get appBarBackground => surface;

  /// The title text in the app bar. Example: the 'Trips' title.
  Color get appBarTitle => textPrimary;

  /// Tappable icons in the app bar. Example: the back arrow.
  Color get appBarIcon => textPrimary;

  /// The hairline between rows and around containers. Example: the
  /// outline of [AppContainer].
  Color get divider => border;

  /// The color of soft drop shadows, alpha baked in. Example: the shadow
  /// under a raised card.
  Color get shadow => textPrimary.withValues(alpha: 0.05);

  /// The glow under the primary call to action. Example: the halo under
  /// the Save button.
  Color get primaryGlow => primary.withValues(alpha: 0.25);

  /// The fill of [AppContainer] blocks. Example: a trip card.
  Color get containerBackground => surface;

  /// The fill of [PrimaryButton]. Example: the Save button.
  Color get buttonBackground => primary;

  /// The label color inside [PrimaryButton]. Example: the 'Save' text.
  Color get buttonText => textOnPrimary;

  /// The outline of [SecondaryButton]. Example: the Cancel button.
  Color get secondaryButtonBorder => primary;

  /// The label color inside [SecondaryButton]. Example: the 'Cancel' text.
  Color get secondaryButtonText => primary;

  /// The resting outline of [AppTextField]. Example: an empty title field.
  Color get textFieldBorder => border;

  /// The outline of [AppTextField] while it has focus. Example: the title
  /// field while the user types.
  Color get textFieldFocusedBorder => primary;

  /// The spinner of [AppLoader]. Example: the loader while trips load.
  Color get loader => primary;

  /// The fill of small rounded label pills. Example: a soft brand pill on
  /// a trip.
  Color get chipBackground => primaryLight;

  /// The text inside those pills. Example: the label in a brand pill.
  Color get chipText => primaryDark;

  /// The background of the success snackbar. Example: 'Trip saved'.
  Color get snackBarSuccess => success;

  /// The background of the error snackbar. Example: 'Something went
  /// wrong'.
  Color get snackBarError => error;

  /// The text inside snackbars. Example: the message on the error bar.
  Color get snackBarText => textOnPrimary;

  /// The dimmed layer behind dialogs and bottom sheets. Example: the scrim
  /// behind a confirmation sheet.
  Color get overlayBarrier => const Color(0x80000000);

  /// The fill of inverted surfaces such as tooltips. Example: the dark
  /// pill of a tooltip in light mode.
  Color get inverseSurface => textPrimary;

  /// The ink on [inverseSurface]. Example: the text inside a tooltip.
  Color get onInverseSurface => background;

  /// The fill of bottom sheets. Example: a confirmation sheet.
  Color get bottomSheetBackground => surface;

  /// The fill of dialogs. Example: a confirmation dialog.
  Color get dialogBackground => surface;
'''
BASE_SLOTS = re.findall(r'Color get (\w+);', APP_SKIN_SLOTS)
DERIVED_SLOTS = re.findall(r'Color get (\w+) =>', APP_SKIN_SLOTS)


def name_set(name, slots):
    return '  static const ' + name + ' = {\n' + ''.join("    '%s',\n" % s for s in slots) + '  };\n'


APP_SKIN = ('''
import 'package:flutter/material.dart';

abstract class AppSkin {
  const AppSkin();

''' + name_set('baseSlotNames', BASE_SLOTS) + '\n' + name_set('derivedSlotNames', DERIVED_SLOTS) + '''
  /// A stable id, used to persist the user's choice. Skins are equal by id.
  /// Example: 'light' for [LightSkin].
  String get id;

  /// The name shown for this skin. Example: 'Light'.
  String displayName(Locale locale);

  /// Light or dark: sets the brightness of the status bar, the keyboard and
  /// Material's own widgets. Example: LightSkin returns [ThemeMode.light].
  ThemeMode get themeMode;

  @override
  bool operator ==(Object other) => other is AppSkin && other.id == id;

  @override
  int get hashCode => id.hashCode;
''' + APP_SKIN_SLOTS + '}\n')

LIGHT = {'background': 'FFF7F8FA', 'surface': 'FFFFFFFF', 'card': 'FFF0F2F5', 'border': 'FFE5E7EB',
         'primary': 'FF1E6FD9', 'primaryDark': 'FF1553A6', 'primaryLight': 'FFE3EEFC', 'accent': 'FF0EA5E9',
         'accentLight': 'FFE0F4FD', 'textPrimary': 'FF1A1C1E', 'textSecondary': 'FF6B7280', 'textMuted': 'FF9CA3AF',
         'textOnPrimary': 'FFFFFFFF', 'success': 'FF16A34A', 'successLight': 'FFE3F6EA', 'error': 'FFDC2626',
         'errorLight': 'FFFCE7E7', 'warning': 'FFF59E0B', 'warningLight': 'FFFEF3DC'}
DARK = {'background': 'FF111316', 'surface': 'FF1A1D21', 'card': 'FF0C0E10', 'border': '1FFFFFFF',
        'primary': 'FF5B9BF0', 'primaryDark': 'FF9CC3F7', 'primaryLight': '295B9BF0', 'accent': 'FF7DD3FC',
        'accentLight': '247DD3FC', 'textPrimary': 'FFF3F4F6', 'textSecondary': 'FFA1A7B0', 'textMuted': 'FF6B7280',
        'textOnPrimary': 'FF0B1220', 'success': 'FF4ADE80', 'successLight': '294ADE80', 'error': 'FFF87171',
        'errorLight': '29F87171', 'warning': 'FFFBBF24', 'warningLight': '29FBBF24'}
DARK_OVERRIDES = {'shadow': '80000000', 'bottomSheetBackground': 'FF23272C', 'dialogBackground': 'FF23272C'}
OCEAN = {'background': 'FF0B1A24', 'surface': 'FF102633', 'card': 'FF07131B', 'border': '1FFFFFFF',
         'primary': 'FF2DD4BF', 'primaryDark': 'FF99F6E4', 'primaryLight': '292DD4BF', 'accent': 'FF38BDF8',
         'accentLight': '2438BDF8', 'textPrimary': 'FFE6F1F5', 'textSecondary': 'FF94A9B5', 'textMuted': 'FF5F7684',
         'textOnPrimary': 'FF04201C', 'success': 'FF4ADE80', 'successLight': '294ADE80', 'error': 'FFF87171',
         'errorLight': '29F87171', 'warning': 'FFFBBF24', 'warningLight': '29FBBF24'}
OCEAN_OVERRIDES = {'shadow': '80000000', 'bottomSheetBackground': 'FF173444', 'dialogBackground': 'FF173444'}


def built_in_skin(cls, skin_id, key, mode, colors, overrides):
    getters = ''.join('\n  @override\n  Color get %s => const Color(0x%s);\n' % (s, colors[s]) for s in BASE_SLOTS)
    getters += ''.join('\n  @override\n  Color get %s => const Color(0x%s);\n' % (s, v) for s, v in overrides.items())
    return ('''
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:app/core/l10n/locale_keys.g.dart';
import 'package:app/core/theme/skin/app_skin.dart';

class %s extends AppSkin {
  const %s();

  @override
  String get id => '%s';

  @override
  String displayName(Locale locale) => LocaleKeys.%s.tr();

  @override
  ThemeMode get themeMode => ThemeMode.%s;
''' % (cls, cls, skin_id, key, mode)) + getters + '}\n'


def json_skin_file(skin_id, mode, en, ar, colors, overrides):
    def block(d):
        return ',\n'.join('    "%s": "#%s"' % (k, v) for k, v in d.items())
    return ('{\n  "id": "%s",\n  "mode": "%s",\n  "name": {\n    "en": "%s",\n    "ar": "%s"\n  },\n'
            '  "colors": {\n%s\n  },\n  "overrides": {\n%s\n  }\n}\n') % (
        skin_id, mode, en, ar, block({s: colors[s] for s in BASE_SLOTS}), block(overrides))


def app_tokens(motion):
    m_import = "import 'package:app/core/theme/motion/app_motion.dart';\n" if motion else ''
    m_param = '    required this.motion,\n' if motion else ''
    m_field = '  final AppMotion motion;\n' if motion else ''
    m_std = '    motion: AppMotion.standard,\n' if motion else ''
    m_std6 = '        motion: AppMotion.standard,\n' if motion else ''
    m_cw_param = '    AppMotion? motion,\n' if motion else ''
    m_cw = '      motion: motion ?? this.motion,\n' if motion else ''
    m_lerp = '      motion: motion,\n' if motion else ''
    return '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/app_elevation.dart';
import 'package:app/core/theme/app_radius.dart';
import 'package:app/core/theme/app_spacing.dart';
''' + m_import + '''import 'package:app/core/theme/skin/app_skin.dart';
import 'package:app/core/theme/skin/dark_skin.dart';
import 'package:app/core/theme/skin/light_skin.dart';
import 'package:app/core/theme/typography/app_typography.dart';

@immutable
class AppTokens extends ThemeExtension<AppTokens> {
  const AppTokens({
    required this.skin,
    required this.space,
    required this.radius,
    required this.text,
    required this.elevation,
''' + m_param + '''  });

  final AppSkin skin;
  final AppSpacing space;
  final AppRadius radius;
  final AppTypography text;
  final AppElevation elevation;
''' + m_field + '''
  static const light = AppTokens(
    skin: LightSkin(),
    space: AppSpacing.standard,
    radius: AppRadius.standard,
    text: AppTypography.standard,
    elevation: AppElevation(LightSkin()),
''' + m_std + '''  );

  static const dark = AppTokens(
    skin: DarkSkin(),
    space: AppSpacing.standard,
    radius: AppRadius.standard,
    text: AppTypography.standard,
    elevation: AppElevation(DarkSkin()),
''' + m_std + '''  );

  static final Map<String, AppTokens> _cache = {};

  static AppTokens of(AppSkin skin) {
    if (skin == light.skin) return light;
    if (skin == dark.skin) return dark;
    return _cache.putIfAbsent(
      skin.id,
      () => AppTokens(
        skin: skin,
        space: AppSpacing.standard,
        radius: AppRadius.standard,
        text: AppTypography.standard,
        elevation: AppElevation(skin),
''' + m_std6 + '''      ),
    );
  }

  @override
  AppTokens copyWith({
    AppSkin? skin,
    AppSpacing? space,
    AppRadius? radius,
    AppTypography? text,
    AppElevation? elevation,
''' + m_cw_param + '''  }) {
    return AppTokens(
      skin: skin ?? this.skin,
      space: space ?? this.space,
      radius: radius ?? this.radius,
      text: text ?? this.text,
      elevation: elevation ?? this.elevation,
''' + m_cw + '''    );
  }

  @override
  AppTokens lerp(ThemeExtension<AppTokens>? other, double t) {
    if (other is! AppTokens) return this;
    final near = t < 0.5 ? this : other;
    return AppTokens(
      skin: near.skin,
      space: space,
      radius: radius,
      text: text,
      elevation: near.elevation,
''' + m_lerp + '''    );
  }
}

extension AppTokensContext on BuildContext {
  AppTokens get tokens {
    final tokens = Theme.of(this).extension<AppTokens>();
    if (tokens == null) {
      throw FlutterError(
        'AppTokens is not registered on ThemeData.extensions. '
        'Build the theme with AppTheme.light, AppTheme.dark or AppTheme.of.',
      );
    }
    return tokens;
  }
}
'''


THEME = {
    'lib/core/theme/skin/app_skin.dart': APP_SKIN,
    'lib/core/theme/skin/light_skin.dart': built_in_skin('LightSkin', 'light', 'themeLight', 'light', LIGHT, {}),
    'lib/core/theme/skin/dark_skin.dart': built_in_skin('DarkSkin', 'dark', 'themeDark', 'dark', DARK, DARK_OVERRIDES),
    'lib/core/theme/app_tokens.dart': app_tokens(False),
    'lib/core/theme/app_spacing.dart': '''
import 'package:flutter/widgets.dart';

@immutable
class AppSpacing {
  const AppSpacing();

  static const standard = AppSpacing();

  double get xs => 4;
  double get sm => 8;
  double get md => 12;
  double get lg => 16;
  double get xl => 20;
  double get xxl => 24;
  double get xxxl => 32;

  double get screenHValue => 16;

  EdgeInsets get screenH => const EdgeInsets.symmetric(horizontal: 16);
}
''',
    'lib/core/theme/app_radius.dart': '''
import 'package:flutter/widgets.dart';

@immutable
class AppRadius {
  const AppRadius();

  static const standard = AppRadius();

  double get xsValue => 4;
  double get smValue => 8;
  double get mdValue => 12;
  double get lgValue => 16;
  double get xlValue => 20;
  double get pillValue => 999;

  BorderRadius get xs => BorderRadius.circular(xsValue);
  BorderRadius get sm => BorderRadius.circular(smValue);
  BorderRadius get md => BorderRadius.circular(mdValue);
  BorderRadius get lg => BorderRadius.circular(lgValue);
  BorderRadius get xl => BorderRadius.circular(xlValue);
  BorderRadius get pill => BorderRadius.circular(pillValue);

  BorderRadius get card => md;
  BorderRadius get input => sm;
  BorderRadius get button => pill;
  BorderRadius get sheet => BorderRadius.vertical(top: Radius.circular(xlValue));
}
''',
    'lib/core/theme/app_elevation.dart': '''
import 'package:flutter/widgets.dart';
import 'package:app/core/theme/skin/app_skin.dart';

@immutable
class AppElevation {
  const AppElevation(this.skin);

  final AppSkin skin;

  List<BoxShadow> get low => [
        BoxShadow(color: skin.shadow, blurRadius: 2, offset: const Offset(0, 1)),
      ];

  List<BoxShadow> get high => [
        BoxShadow(color: skin.shadow, blurRadius: 24, offset: const Offset(0, 8)),
      ];

  List<BoxShadow> glow({Color? color}) => [
        BoxShadow(color: color ?? skin.primaryGlow, blurRadius: 18, offset: const Offset(0, 6)),
      ];
}
''',
    'lib/core/theme/typography/font_weight_helper.dart': '''
import 'dart:ui';

sealed class FontWeightHelper {
  static const FontWeight light = FontWeight.w300;
  static const FontWeight regular = FontWeight.w400;
  static const FontWeight medium = FontWeight.w500;
  static const FontWeight semiBold = FontWeight.w600;
  static const FontWeight bold = FontWeight.w700;
}
''',
    'lib/core/theme/typography/app_typography.dart': '''
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:app/core/theme/typography/font_weight_helper.dart';

@immutable
class AppTypography {
  const AppTypography();

  static const standard = AppTypography();

  static TextStyle _textStyle(double size, FontWeight weight, {double? height, double tracking = 0}) {
    return TextStyle(
      fontSize: size.spMin,
      fontWeight: weight,
      height: height,
      letterSpacing: tracking == 0 ? null : size.spMin * tracking,
    );
  }

  /// Screen titles. Example: 'Trips' in the app bar.
  TextStyle get headingMd => _textStyle(18, FontWeightHelper.bold, height: 1.3);

  /// Card and row titles. Example: a trip's title in the list.
  TextStyle get headingSm => _textStyle(16, FontWeightHelper.medium, height: 1.4);

  /// Body copy. Example: an error message.
  TextStyle get bodyMd => _textStyle(14, FontWeightHelper.regular, height: 1.5);

  /// Emphasised short labels. Example: the 'Save' label and a trip's price.
  TextStyle get labelMd => _textStyle(14, FontWeightHelper.medium, height: 1.4);

  /// Secondary copy and meta. Example: a trip's destination.
  TextStyle get caption => _textStyle(12, FontWeightHelper.regular, height: 1.4);

  TextStyle get style12Regular => _textStyle(12, FontWeightHelper.regular);

  TextStyle get style14Regular => _textStyle(14, FontWeightHelper.regular);

  TextStyle get style14Medium => _textStyle(14, FontWeightHelper.medium);

  TextStyle get style16Medium => _textStyle(16, FontWeightHelper.medium);

  TextStyle get style18Bold => _textStyle(18, FontWeightHelper.bold);
}
''',
    'lib/core/theme/app_theme.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/app_tokens.dart';
import 'package:app/core/theme/skin/app_skin.dart';

abstract final class AppTheme {
  static ThemeData get light => _build(AppTokens.light);

  static ThemeData get dark => _build(AppTokens.dark);

  static ThemeData of(AppSkin skin) => _build(AppTokens.of(skin));

  static ThemeData _build(AppTokens tokens) {
    final skin = tokens.skin;
    final brightness = skin.themeMode == ThemeMode.dark ? Brightness.dark : Brightness.light;
    return ThemeData(
      useMaterial3: true,
      extensions: [tokens],
      brightness: brightness,
      scaffoldBackgroundColor: skin.background,
      appBarTheme: AppBarTheme(
        backgroundColor: skin.appBarBackground,
        titleTextStyle: tokens.text.headingMd.copyWith(color: skin.appBarTitle),
        iconTheme: IconThemeData(color: skin.appBarIcon),
        actionsIconTheme: IconThemeData(color: skin.appBarIcon),
        surfaceTintColor: Colors.transparent,
        elevation: 0,
      ),
      colorScheme: ColorScheme.fromSeed(
        seedColor: skin.primary,
        brightness: brightness,
        primary: skin.primary,
        onPrimary: skin.textOnPrimary,
        primaryContainer: skin.primaryLight,
        onPrimaryContainer: skin.primaryDark,
        inversePrimary: skin.primary,
        secondary: skin.accent,
        onSecondary: skin.textOnPrimary,
        secondaryContainer: skin.accentLight,
        onSecondaryContainer: skin.accent,
        tertiary: skin.accent,
        onTertiary: skin.textOnPrimary,
        tertiaryContainer: skin.accentLight,
        onTertiaryContainer: skin.accent,
        surface: skin.surface,
        onSurface: skin.textPrimary,
        onSurfaceVariant: skin.textSecondary,
        surfaceContainerLowest: skin.card,
        surfaceContainerLow: skin.background,
        surfaceContainer: skin.surface,
        surfaceContainerHigh: skin.surface,
        surfaceContainerHighest: skin.surface,
        surfaceTint: skin.primary,
        inverseSurface: skin.inverseSurface,
        onInverseSurface: skin.onInverseSurface,
        outline: skin.border,
        outlineVariant: skin.divider,
        error: skin.error,
        onError: skin.textOnPrimary,
        errorContainer: skin.errorLight,
        onErrorContainer: skin.error,
      ),
      dialogTheme: DialogThemeData(backgroundColor: skin.dialogBackground, barrierColor: skin.overlayBarrier),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: skin.bottomSheetBackground,
        modalBarrierColor: skin.overlayBarrier,
        surfaceTintColor: Colors.transparent,
        shape: RoundedRectangleBorder(borderRadius: tokens.radius.sheet),
      ),
      dividerColor: skin.divider,
    );
  }
}
''',
}

# ---------- core widgets, grouped by role, reading every value from context.tokens ----------
WIDGETS = {
    'lib/core/widgets/text/app_text.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/app_tokens.dart';

class AppText extends StatelessWidget {
  const AppText(this.text, {super.key, this.style, this.maxLines, this.textAlign});

  final String text;
  final TextStyle? style;
  final int? maxLines;
  final TextAlign? textAlign;

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    final base = style ?? tokens.text.bodyMd;
    return Text(
      text,
      style: base.color == null ? base.copyWith(color: tokens.skin.textPrimary) : base,
      maxLines: maxLines,
      overflow: maxLines == null ? null : TextOverflow.ellipsis,
      textAlign: textAlign,
    );
  }
}
''',
    'lib/core/widgets/text/bullet_text.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/app_tokens.dart';
import 'package:app/core/widgets/layout/space_widgets.dart';
import 'package:app/core/widgets/text/app_text.dart';

class BulletText extends StatelessWidget {
  const BulletText(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        AppText('•', style: tokens.text.bodyMd.copyWith(color: tokens.skin.textSecondary)),
        HorizontalSpace(tokens.space.sm),
        Expanded(child: AppText(text, maxLines: 3)),
      ],
    );
  }
}
''',
    'lib/core/widgets/layout/app_scaffold.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/app_tokens.dart';

class AppScaffold extends StatelessWidget {
  const AppScaffold({
    super.key,
    required this.body,
    this.appBar,
    this.floatingActionButton,
    this.bottomNavigationBar,
  });

  final Widget body;
  final PreferredSizeWidget? appBar;
  final Widget? floatingActionButton;
  final Widget? bottomNavigationBar;

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: context.tokens.skin.background,
        appBar: appBar,
        body: SafeArea(child: body),
        floatingActionButton: floatingActionButton,
        bottomNavigationBar: bottomNavigationBar,
      );
}
''',
    'lib/core/widgets/layout/global_appbar.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/app_tokens.dart';

class GlobalAppbar extends StatelessWidget implements PreferredSizeWidget {
  const GlobalAppbar.main({super.key, required this.titleText, this.actions}) : showBack = false;

  const GlobalAppbar.sub({super.key, required this.titleText, this.actions}) : showBack = true;

  final String titleText;
  final List<Widget>? actions;
  final bool showBack;

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    return AppBar(
      backgroundColor: tokens.skin.appBarBackground,
      automaticallyImplyLeading: showBack,
      title: Text(titleText, style: tokens.text.headingMd.copyWith(color: tokens.skin.appBarTitle)),
      actions: actions,
    );
  }
}
''',
    'lib/core/widgets/layout/space_widgets.dart': '''
import 'package:flutter/material.dart';

class VerticalSpace extends StatelessWidget {
  const VerticalSpace(this.height, {super.key});

  final double height;

  @override
  Widget build(BuildContext context) => SizedBox(height: height);
}

class HorizontalSpace extends StatelessWidget {
  const HorizontalSpace(this.width, {super.key});

  final double width;

  @override
  Widget build(BuildContext context) => SizedBox(width: width);
}
''',
    'lib/core/widgets/layout/app_container.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/app_tokens.dart';

class AppContainer extends StatelessWidget {
  const AppContainer({super.key, required this.child, this.padding});

  final Widget child;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    return Container(
      padding: padding ?? EdgeInsets.all(tokens.space.md),
      decoration: BoxDecoration(
        color: tokens.skin.containerBackground,
        borderRadius: tokens.radius.card,
        border: Border.all(color: tokens.skin.divider),
      ),
      child: child,
    );
  }
}
''',
    'lib/core/widgets/buttons/primary_button.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/app_tokens.dart';
import 'package:app/core/widgets/feedback/app_loader.dart';
import 'package:app/core/widgets/text/app_text.dart';

class PrimaryButton extends StatelessWidget {
  const PrimaryButton({super.key, required this.text, required this.onPressed, this.isLoading = false, this.backgroundColor})
      : expand = false;

  const PrimaryButton.expand({super.key, required this.text, required this.onPressed, this.isLoading = false, this.backgroundColor})
      : expand = true;

  final String text;
  final VoidCallback? onPressed;
  final bool isLoading;
  final bool expand;
  final Color? backgroundColor;

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    final button = ElevatedButton(
      style: ElevatedButton.styleFrom(
        backgroundColor: backgroundColor ?? tokens.skin.buttonBackground,
        shape: RoundedRectangleBorder(borderRadius: tokens.radius.button),
      ),
      onPressed: isLoading ? null : onPressed,
      child: isLoading
          ? const AppLoader(size: 18)
          : AppText(text, style: tokens.text.labelMd.copyWith(color: tokens.skin.buttonText)),
    );
    return expand ? SizedBox(width: double.infinity, child: button) : button;
  }
}
''',
    'lib/core/widgets/buttons/secondary_button.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/app_tokens.dart';
import 'package:app/core/widgets/text/app_text.dart';

class SecondaryButton extends StatelessWidget {
  const SecondaryButton({super.key, required this.text, required this.onPressed}) : expand = false;

  const SecondaryButton.expand({super.key, required this.text, required this.onPressed}) : expand = true;

  final String text;
  final VoidCallback? onPressed;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    final button = OutlinedButton(
      style: OutlinedButton.styleFrom(
        side: BorderSide(color: tokens.skin.secondaryButtonBorder),
        shape: RoundedRectangleBorder(borderRadius: tokens.radius.button),
      ),
      onPressed: onPressed,
      child: AppText(text, style: tokens.text.labelMd.copyWith(color: tokens.skin.secondaryButtonText)),
    );
    return expand ? SizedBox(width: double.infinity, child: button) : button;
  }
}
''',
    'lib/core/widgets/inputs/app_text_field.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/app_tokens.dart';

class AppTextField extends StatelessWidget {
  const AppTextField({
    super.key,
    this.controller,
    this.hintText,
    this.validator,
    this.maxLines = 1,
    this.keyboardType,
  });

  final TextEditingController? controller;
  final String? hintText;
  final String? Function(String?)? validator;
  final int maxLines;
  final TextInputType? keyboardType;

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    return TextFormField(
      controller: controller,
      validator: validator,
      maxLines: maxLines,
      keyboardType: keyboardType,
      style: tokens.text.bodyMd.copyWith(color: tokens.skin.textPrimary),
      decoration: InputDecoration(
        hintText: hintText,
        hintStyle: tokens.text.bodyMd.copyWith(color: tokens.skin.textMuted),
        enabledBorder: OutlineInputBorder(
          borderRadius: tokens.radius.input,
          borderSide: BorderSide(color: tokens.skin.textFieldBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: tokens.radius.input,
          borderSide: BorderSide(color: tokens.skin.textFieldFocusedBorder),
        ),
      ),
    );
  }
}
''',
    'lib/core/widgets/inputs/app_check_box.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/app_tokens.dart';

class AppCheckBox extends StatelessWidget {
  const AppCheckBox({super.key, required this.value, required this.onChanged});

  final bool value;
  final ValueChanged<bool?>? onChanged;

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    return Checkbox(
      value: value,
      onChanged: onChanged,
      activeColor: tokens.skin.primary,
      checkColor: tokens.skin.textOnPrimary,
      side: BorderSide(color: tokens.skin.border),
    );
  }
}
''',
    'lib/core/widgets/feedback/app_loader.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/app_tokens.dart';

class AppLoader extends StatelessWidget {
  const AppLoader({super.key, this.size = 32});

  final double size;

  @override
  Widget build(BuildContext context) => Center(
        child: SizedBox.square(
          dimension: size,
          child: CircularProgressIndicator(color: context.tokens.skin.loader),
        ),
      );
}
''',
    'lib/core/widgets/feedback/app_error_widget.dart': '''
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:app/core/l10n/locale_keys.g.dart';
import 'package:app/core/theme/app_tokens.dart';
import 'package:app/core/widgets/buttons/primary_button.dart';
import 'package:app/core/widgets/layout/space_widgets.dart';
import 'package:app/core/widgets/text/app_text.dart';

class AppErrorWidget extends StatelessWidget {
  const AppErrorWidget({super.key, required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AppText(message, textAlign: TextAlign.center),
            if (onRetry != null) ...[
              VerticalSpace(context.tokens.space.md),
              PrimaryButton(text: LocaleKeys.retry.tr(), onPressed: onRetry),
            ],
          ],
        ),
      );
}
''',
}

CORE = {
    # ---------- data: api ----------
    'lib/core/data/api/api_consumer.dart': '''
import 'package:dio/dio.dart';

abstract class ApiConsumer {
  Future<Response> get(String path, {Map<String, dynamic>? queryParameters});

  Future<Response> post(String path, {Object? body, Map<String, dynamic>? queryParameters});

  Future<Response> put(String path, {Object? body});

  Future<Response> delete(String path, {Object? body});
}
''',
    'lib/core/data/api/dio_consumer.dart': '''
import 'package:dio/dio.dart';
import 'package:app/core/data/api/api_consumer.dart';
import 'package:app/core/data/error_handling/failure.dart';

class DioConsumer implements ApiConsumer {
  DioConsumer(this._dio);

  final Dio _dio;

  Future<Response> _guard(Future<Response> Function() call) async {
    try {
      return await call();
    } on DioException catch (error) {
      throw ServerFailure.fromDio(error);
    }
  }

  @override
  Future<Response> get(String path, {Map<String, dynamic>? queryParameters}) =>
      _guard(() => _dio.get(path, queryParameters: queryParameters));

  @override
  Future<Response> post(String path, {Object? body, Map<String, dynamic>? queryParameters}) =>
      _guard(() => _dio.post(path, data: body, queryParameters: queryParameters));

  @override
  Future<Response> put(String path, {Object? body}) => _guard(() => _dio.put(path, data: body));

  @override
  Future<Response> delete(String path, {Object? body}) => _guard(() => _dio.delete(path, data: body));
}
''',
    'lib/core/data/api/end_points.dart': '''
sealed class EndPoints {
  static const String baseUrl = 'https://api.example.com';

  static const String orders = '/orders';
}
''',
    'lib/core/data/api/global_response.dart': '''
import 'package:equatable/equatable.dart';

class GlobalResponse<T> extends Equatable {
  final T? data;
  final String? message;
  final bool? status;

  const GlobalResponse({this.data, this.message, this.status});

  factory GlobalResponse.fromJson(
    Map<String, dynamic> json, {
    T Function(dynamic json)? fromJsonT,
    bool withDataKey = true,
  }) {
    final raw = withDataKey ? json['data'] : json;
    return GlobalResponse(
      data: fromJsonT != null && raw != null ? fromJsonT(raw) : raw as T?,
      message: json['message'] as String?,
      status: json['status'] as bool?,
    );
  }

  @override
  List<Object?> get props => [data, message, status];
}
''',
    # ---------- data: errors ----------
    'lib/core/data/error_handling/failure.dart': '''
import 'package:dio/dio.dart';
import 'package:equatable/equatable.dart';

abstract class Failure extends Equatable implements Exception {
  final String message;

  const Failure(this.message);

  @override
  List<Object?> get props => [message];
}

class ServerFailure extends Failure {
  const ServerFailure(super.message);

  factory ServerFailure.noNetwork() => const ServerFailure('No internet connection');

  factory ServerFailure.fromDio(DioException error) => ServerFailure(error.message ?? 'Something went wrong');
}

class LocalFailure extends Failure {
  const LocalFailure(super.message);

  factory LocalFailure.fromDrift(Object error, StackTrace stackTrace) => LocalFailure(error.toString());

  factory LocalFailure.fromHive(Object error, StackTrace stackTrace) => LocalFailure(error.toString());
}
''',
    'lib/core/data/error_handling/result.dart': '''
import 'package:app/core/data/error_handling/failure.dart';

typedef FutureResult<T> = Future<Result<T>>;

sealed class Result<T> {
  const Result();

  factory Result.success(T data) = Success<T>;

  factory Result.failure(Failure failure) = Error<T>;

  R when<R>({
    required R Function(T data) onSuccess,
    required R Function(Failure failure) onFailure,
  }) =>
      switch (this) {
        Success<T>(:final data) => onSuccess(data),
        Error<T>(:final failure) => onFailure(failure),
      };
}

final class Success<T> extends Result<T> {
  const Success(this.data);

  final T data;
}

final class Error<T> extends Result<T> {
  const Error(this.failure);

  final Failure failure;
}
''',
    # ---------- services ----------
    'lib/core/services/network_status.dart': '''
import 'package:connectivity_plus/connectivity_plus.dart';

abstract class NetworkStatus {
  Future<bool> get isConnected;
}

class NetworkStatusImp implements NetworkStatus {
  NetworkStatusImp(this._connectivity);

  final Connectivity _connectivity;

  @override
  Future<bool> get isConnected async {
    final result = await _connectivity.checkConnectivity();
    return !result.contains(ConnectivityResult.none);
  }
}
''',
    # ---------- l10n ----------
    'lib/core/l10n/app_locales.dart': '''
import 'dart:ui';

abstract final class AppLocales {
  static const path = 'assets/translations';
  static const en = Locale('en');
  static const ar = Locale('ar');
  static const supported = [en, ar];
  static const fallback = en;
}
''',
    'lib/core/l10n/locale_keys.g.dart': locale_keys(BASE_KEYS),
    # ---------- helpers ----------
    'lib/core/helpers/app_form_validations.dart': '''
import 'package:easy_localization/easy_localization.dart';
import 'package:app/core/l10n/locale_keys.g.dart';

sealed class AppFormValidations {
  static String? requiredField(String? value) =>
      (value == null || value.trim().isEmpty) ? LocaleKeys.fieldIsRequired.tr() : null;
}
''',
    'lib/core/helpers/extensions/snackbar_extensions.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/app_tokens.dart';
import 'package:app/core/widgets/text/app_text.dart';

extension ShowSnackbarExtension on BuildContext {
  void showSnackBar(String message) => _show(message, tokens.skin.snackBarSuccess);

  void showErrorSnackBar(String message) => _show(message, tokens.skin.snackBarError);

  void _show(String message, Color background) {
    ScaffoldMessenger.of(this).showSnackBar(
      SnackBar(
        content: AppText(message, style: tokens.text.bodyMd.copyWith(color: tokens.skin.snackBarText)),
        backgroundColor: background,
      ),
    );
  }
}
''',
    'lib/core/helpers/extensions/router_extensions.dart': '''
part of '../../router/app_router.dart';

extension Navigation on BuildContext {
  Future<dynamic> pushNamed(String routeName, {Object? arguments}) {
    return Navigator.of(this, rootNavigator: true).pushNamed(routeName, arguments: arguments);
  }

  Future<dynamic> pushReplacementNamed(String routeName, {Object? arguments}) {
    return Navigator.of(this, rootNavigator: true).pushReplacementNamed(routeName, arguments: arguments);
  }

  Future<dynamic> pushNamedAndRemoveUntil(String routeName, RoutePredicate predicate, {Object? arguments}) {
    return Navigator.of(this, rootNavigator: true).pushNamedAndRemoveUntil(routeName, predicate, arguments: arguments);
  }

  void pop<T>([T? result]) => Navigator.pop(this, result);

  void popUntil(RoutePredicate predicate) {
    Navigator.of(this, rootNavigator: true).popUntil(predicate);
  }

  void popToRoot() {
    Navigator.of(this, rootNavigator: true).popUntil((route) => route.isFirst);
  }
}
''',
    # ---------- routing (legacy: RoutesStrings._(), the orders case has no BlocProvider) ----------
    'lib/core/router/routes_strings.dart': '''
part of 'app_router.dart';

class RoutesStrings {
  RoutesStrings._();

  static const String orders = 'orders-screen';
}
''',
    'lib/core/router/app_router.dart': '''
import 'package:flutter/material.dart';
import 'package:app/feature/orders/presentation/orders_screen/ui/orders_screen.dart';

part '../helpers/extensions/router_extensions.dart';
part 'routes_strings.dart';

sealed class AppRouter {
  static final GlobalKey<NavigatorState> navigationKey = GlobalKey<NavigatorState>();

  static final GlobalKey<ScaffoldMessengerState> scaffoldMessengerKey = GlobalKey<ScaffoldMessengerState>();

  static Route<dynamic>? generateRoute(RouteSettings settings) {
    switch (settings.name) {
      case RoutesStrings.orders:
        return MaterialPageRoute(builder: (_) => const OrdersScreen());
    }
    return MaterialPageRoute(
      builder: (context) => const Scaffold(body: Center(child: Text('No Route Found'))),
    );
  }
}
''',
    # ---------- legacy orders feature: every file breaks the conventions ----------
    'lib/feature/orders/orders_injection.dart': '''
import 'package:get_it/get_it.dart';
import 'package:app/feature/orders/data/data_source/orders_remote_data_source.dart';
import 'package:app/feature/orders/data/repository/orders_repository.dart';
import 'package:app/feature/orders/presentation/orders_screen/logic/orders_bloc.dart';

void registerOrdersDependencies(GetIt sl) {
  sl.registerLazySingleton(() => OrdersRemoteDataSource(sl()));
  sl.registerLazySingleton(() => OrdersRepository(sl()));
  sl.registerFactory(() => OrdersBloc(sl()));
}
''',
    'lib/feature/orders/data/model/order_model.dart': '''
class OrderModel {
  final String id;
  final String title;
  final double total;

  OrderModel({required this.id, required this.title, required this.total});

  Map<String, dynamic> toJson() => {'id': id, 'title': title, 'total': total};

  factory OrderModel.fromJson(Map<String, dynamic> json) => OrderModel(
        id: json['id'],
        title: json['title'],
        total: (json['total'] as num).toDouble(),
      );
}
''',
    'lib/feature/orders/data/data_source/orders_remote_data_source.dart': '''
import 'package:app/core/data/api/api_consumer.dart';
import 'package:app/core/data/api/end_points.dart';
import 'package:app/feature/orders/data/model/order_model.dart';

class OrdersRemoteDataSource {
  OrdersRemoteDataSource(this.api);

  final ApiConsumer api;

  Future<List<OrderModel>> getOrders() async {
    try {
      final response = await api.get(EndPoints.orders);
      return (response.data['data'] as List).map((e) => OrderModel.fromJson(e)).toList();
    } catch (e) {
      print(e);
      rethrow;
    }
  }

  Future<void> cancelOrder(String id) async {
    await api.post('${EndPoints.orders}/$id/cancel');
  }
}
''',
    'lib/feature/orders/data/repository/orders_repository.dart': '''
import 'package:app/feature/orders/data/data_source/orders_remote_data_source.dart';
import 'package:app/feature/orders/data/model/order_model.dart';

class OrdersRepository {
  OrdersRepository(this.remote);

  final OrdersRemoteDataSource remote;

  Future<List<OrderModel>> getOrders() => remote.getOrders();

  Future<void> cancelOrder(String id) => remote.cancelOrder(id);
}
''',
    'lib/feature/orders/presentation/orders_screen/logic/orders_event.dart': '''
part of 'orders_bloc.dart';

abstract class OrdersEvent {}

class LoadOrders extends OrdersEvent {}
''',
    'lib/feature/orders/presentation/orders_screen/logic/orders_state.dart': '''
part of 'orders_bloc.dart';

abstract class OrdersState {}

class OrdersInitial extends OrdersState {}

class OrdersLoading extends OrdersState {}

class OrdersLoaded extends OrdersState {
  OrdersLoaded(this.orders);

  final List<OrderModel> orders;
}

class OrdersError extends OrdersState {
  OrdersError(this.message);

  final String message;
}
''',
    'lib/feature/orders/presentation/orders_screen/logic/orders_bloc.dart': '''
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:app/feature/orders/data/model/order_model.dart';
import 'package:app/feature/orders/data/repository/orders_repository.dart';

part 'orders_event.dart';
part 'orders_state.dart';

class OrdersBloc extends Bloc<OrdersEvent, OrdersState> {
  OrdersBloc(this.repository) : super(OrdersInitial()) {
    on<LoadOrders>((event, emit) async {
      emit(OrdersLoading());
      try {
        emit(OrdersLoaded(await repository.getOrders()));
      } catch (e) {
        emit(OrdersError(e.toString()));
      }
    });
  }

  final OrdersRepository repository;
}
''',
    'lib/feature/orders/presentation/orders_screen/ui/orders_screen.dart': '''
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:app/core/di/injection.dart';
import 'package:app/feature/orders/presentation/orders_screen/logic/orders_bloc.dart';

class OrdersScreen extends StatefulWidget {
  const OrdersScreen({super.key});

  @override
  State<OrdersScreen> createState() => _OrdersScreenState();
}

class _OrdersScreenState extends State<OrdersScreen> {
  late final OrdersBloc bloc;

  @override
  void initState() {
    super.initState();
    bloc = sl<OrdersBloc>()..add(LoadOrders());
  }

  Widget _buildBody() {
    return BlocBuilder<OrdersBloc, OrdersState>(
      builder: (context, state) {
        if (state is OrdersLoading) {
          return const Center(child: CircularProgressIndicator());
        }
        if (state is OrdersError) {
          WidgetsBinding.instance.addPostFrameCallback((_) {
            ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(state.message)));
          });
          return const Center(child: Text('Something went wrong'));
        }
        if (state is OrdersLoaded) {
          return ListView(
            children: state.orders.map((o) => _OrderTile(title: o.title, total: o.total)).toList(),
          );
        }
        return const SizedBox();
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return BlocProvider.value(
      value: bloc,
      child: Scaffold(
        appBar: AppBar(title: const Text('Orders')),
        body: Padding(padding: EdgeInsets.all(16.w), child: _buildBody()),
      ),
    );
  }
}

class _OrderTile extends StatelessWidget {
  const _OrderTile({required this.title, required this.total});

  final String title;
  final double total;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: EdgeInsets.only(bottom: 8.h),
      padding: EdgeInsets.all(12.r),
      color: const Color(0xFFFFFFFF),
      child: Row(
        children: [
          Expanded(child: Text(title, style: TextStyle(fontSize: 16.sp, fontWeight: FontWeight.bold))),
          Text('\\$${total.toStringAsFixed(2)}', style: TextStyle(fontSize: 14.sp, color: const Color(0xFF1E6FD9))),
        ],
      ),
    );
  }
}
''',
}

PUBSPEC = '''
name: app
environment:
  sdk: ^3.5.0
dependencies:
  flutter:
    sdk: flutter
  flutter_bloc: ^9.0.0
  equatable: ^2.0.5
  get_it: ^8.0.0
  easy_localization: ^3.0.7
  talker: ^4.0.0
  dio: ^5.7.0
  connectivity_plus: ^6.0.5
  flutter_screenutil: ^5.9.3
{extra_deps}
dev_dependencies:
  flutter_test:
    sdk: flutter
{extra_dev}
flutter:
  assets:
    - assets/translations/
{extra_assets}'''


def pubspec(deps='', dev='', assets=''):
    return PUBSPEC.replace('{extra_deps}', deps).replace('{extra_dev}', dev).replace('{extra_assets}', assets)


DRIFT_DEPS = '  drift: ^2.20.0\n  drift_flutter: ^0.2.0'
DRIFT_DEV = '  drift_dev: ^2.20.0\n  build_runner: ^2.4.0'


def core_injection(imports, body):
    return ('''
import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:get_it/get_it.dart';
import 'package:app/core/data/api/api_consumer.dart';
import 'package:app/core/data/api/dio_consumer.dart';
import 'package:app/core/data/api/end_points.dart';
''' + imports + '''import 'package:app/core/services/network_status.dart';

final GetIt sl = GetIt.instance;

void registerCoreDependencies(GetIt sl) {
  /// External Packages
  sl.registerLazySingleton<Dio>(() => Dio(BaseOptions(baseUrl: EndPoints.baseUrl)));

  /// Network
  sl.registerLazySingleton<ApiConsumer>(() => DioConsumer(sl<Dio>()));
  sl.registerLazySingleton<NetworkStatus>(() => NetworkStatusImp(Connectivity()));
''' + body + '}\n')


DRIFT_CORE_IMPORTS = "import 'package:app/core/data/database/app_database.dart';\n"
DRIFT_CORE_BODY = '''
  /// Database
  sl.registerLazySingleton<AppDatabase>(() => AppDatabase());

  // budget
  sl.registerLazySingleton(() => BudgetLocalDataSource(sl()));
'''
DRIFT_CORE_FEATURE_IMPORT = "import 'package:app/feature/budget/data/data_source/local/budget_local_data_source.dart';\n"


def app_injection(features):
    imports = ["import 'package:app/core/di/injection.dart';"] + [
        "import 'package:app/feature/%s/%s_injection.dart';" % (f, f) for f in features]
    calls = ''.join('  register%sDependencies(sl);\n' % f.title() for f in features)
    return ("import 'package:get_it/get_it.dart';\n" + '\n'.join(imports) + '\n\n'
            'void registerAppDependencies(GetIt sl) {\n  registerCoreDependencies(sl);\n' + calls + '}\n')


def injection_test(core, features):
    """core/features: lists of (import path under lib/, class name)."""
    imports = sorted({p for p, _ in core + features})
    lines = lambda pairs: ''.join('    expect(locator.isRegistered<%s>(), isTrue);\n' % c for _, c in pairs)
    return ("import 'package:flutter_test/flutter_test.dart';\nimport 'package:get_it/get_it.dart';\n"
            "import 'package:app/app_injection.dart';\n"
            + ''.join("import 'package:app/%s';\n" % p for p in imports) + '''
void main() {
  late GetIt locator;

  setUp(() {
    locator = GetIt.asNewInstance();
    registerAppDependencies(locator);
  });

  tearDown(() => locator.reset());

  test('core services are registered', () {
''' + lines(core) + '''  });

  test('every feature registers its cubits, repository and data sources', () {
''' + lines(features) + '''  });
}
''')


CORE_TYPES = [('core/data/api/api_consumer.dart', 'ApiConsumer'), ('core/services/network_status.dart', 'NetworkStatus')]
ORDERS_TYPES = [('feature/orders/presentation/orders_screen/logic/orders_bloc.dart', 'OrdersBloc'),
                ('feature/orders/data/repository/orders_repository.dart', 'OrdersRepository'),
                ('feature/orders/data/data_source/orders_remote_data_source.dart', 'OrdersRemoteDataSource')]
DRIFT_CORE_TYPES = CORE_TYPES + [('core/data/database/app_database.dart', 'AppDatabase')]


def main_dart(extra_imports='', before_run=''):
    return ('''
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:app/app_injection.dart';
import 'package:app/core/di/injection.dart';
import 'package:app/core/l10n/app_locales.dart';
''' + extra_imports + '''import 'package:app/my_app.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await EasyLocalization.ensureInitialized();
''' + before_run + '''  runApp(
    EasyLocalization(
      supportedLocales: AppLocales.supported,
      path: AppLocales.path,
      fallbackLocale: AppLocales.fallback,
      child: const MyApp(),
    ),
  );
}
''')


def my_app(initial_route):
    return '''
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:app/core/router/app_router.dart';
import 'package:app/core/theme/app_theme.dart';

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ScreenUtilInit(
      designSize: const Size(375, 812),
      minTextAdapt: true,
      builder: (context, child) => MaterialApp(
        debugShowCheckedModeBanner: false,
        navigatorKey: AppRouter.navigationKey,
        scaffoldMessengerKey: AppRouter.scaffoldMessengerKey,
        theme: AppTheme.light,
        localizationsDelegates: context.localizationDelegates,
        supportedLocales: context.supportedLocales,
        locale: context.locale,
        onGenerateRoute: AppRouter.generateRoute,
        initialRoute: RoutesStrings.%s,
      ),
    );
  }
}
''' % initial_route


def common(root):
    for d in (CORE, THEME, WIDGETS):
        for path, text in d.items():
            w(root, path, text)
    w(root, 'assets/translations/en.json', EN)
    w(root, 'assets/translations/ar.json', AR)
    w(root, 'lib/my_app.dart', my_app('orders'))


def drift(root):
    common(root)
    w(root, 'pubspec.yaml', pubspec(DRIFT_DEPS, DRIFT_DEV))
    w(root, 'lib/core/di/injection.dart', core_injection(DRIFT_CORE_IMPORTS + DRIFT_CORE_FEATURE_IMPORT, DRIFT_CORE_BODY))
    w(root, 'lib/app_injection.dart', app_injection(['orders']))
    w(root, 'lib/main.dart', main_dart(before_run='  registerAppDependencies(sl);\n'))
    w(root, 'test/app_injection_test.dart', injection_test(DRIFT_CORE_TYPES, ORDERS_TYPES))
    w(root, 'lib/core/data/error_handling/drift_error_handler.dart', '''
import 'package:app/core/data/error_handling/failure.dart';

extension DriftFutureFailure<T> on Future<T> {
  Future<T> handleLocalFailure() async {
    try {
      return await this;
    } on Failure {
      rethrow;
    } catch (error, stackTrace) {
      throw LocalFailure.fromDrift(error, stackTrace);
    }
  }
}

extension DriftStreamFailure<T> on Stream<T> {
  Stream<T> handleLocalFailure() => handleError(
        (Object error, StackTrace stackTrace) => throw LocalFailure.fromDrift(error, stackTrace),
        test: (error) => error is! Failure,
      );
}
''')
    w(root, 'lib/core/data/database/app_database.dart', '''
import 'package:drift/drift.dart';
import 'package:drift_flutter/drift_flutter.dart';
import 'package:app/core/data/database/tables/budgets/budgets_dao.dart';
import 'package:app/core/data/database/tables/budgets/budgets_table.dart';

part 'app_database.g.dart';

@DriftDatabase(tables: [Budgets], daos: [BudgetsDao])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(driftDatabase(name: 'app_db'));

  AppDatabase.forTesting(super.executor);

  @override
  int get schemaVersion => 1;

  @override
  MigrationStrategy get migration => MigrationStrategy(
        onCreate: (m) => m.createAll(),
      );
}
''')
    w(root, 'lib/core/data/database/tables/budgets/budgets_table.dart', '''
import 'package:drift/drift.dart';

@DataClassName('BudgetEntity')
class Budgets extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get name => text()();
  RealColumn get amount => real()();
}
''')
    # legacy DAO: no handleLocalFailure
    w(root, 'lib/core/data/database/tables/budgets/budgets_dao.dart', '''
import 'package:drift/drift.dart';
import 'package:app/core/data/database/app_database.dart';
import 'package:app/core/data/database/tables/budgets/budgets_table.dart';

part 'budgets_dao.g.dart';

@DriftAccessor(tables: [Budgets])
class BudgetsDao extends DatabaseAccessor<AppDatabase> with _$BudgetsDaoMixin {
  BudgetsDao(super.db);

  Future<List<BudgetEntity>> getAllBudgets() => select(budgets).get();

  Future<int> insertBudget(BudgetsCompanion entry) => into(budgets).insert(entry);
}
''')
    # legacy budget feature: non-nullable model, params own a drift Companion, concrete data source on
    # AppDatabase, registered untyped in core
    w(root, 'lib/feature/budget/data/models/budget_model.dart', '''
import 'package:app/core/data/database/app_database.dart';

class BudgetModel {
  final int id;
  final String name;
  final double amount;

  BudgetModel({required this.id, required this.name, required this.amount});

  factory BudgetModel.fromDB(BudgetEntity entity) => BudgetModel(id: entity.id, name: entity.name, amount: entity.amount);
}
''')
    w(root, 'lib/feature/budget/domain/params/add_budget_params.dart', '''
import 'package:drift/drift.dart';
import 'package:app/core/data/database/app_database.dart';

class AddBudgetParams {
  final String name;
  final double amount;

  AddBudgetParams({required this.name, required this.amount});

  BudgetsCompanion toDb() => BudgetsCompanion.insert(name: name, amount: amount);
}
''')
    w(root, 'lib/feature/budget/data/data_source/local/budget_local_data_source.dart', '''
import 'package:app/core/data/database/app_database.dart';
import 'package:app/feature/budget/data/models/budget_model.dart';
import 'package:app/feature/budget/domain/params/add_budget_params.dart';

class BudgetLocalDataSource {
  BudgetLocalDataSource(this._db);

  final AppDatabase _db;

  Future<List<BudgetModel>> getBudgets() async {
    final rows = await _db.budgetsDao.getAllBudgets();
    return rows.map(BudgetModel.fromDB).toList();
  }

  Future<int> addBudget(AddBudgetParams params) => _db.budgetsDao.insertBudget(params.toDb());
}
''')


def hive(root):
    common(root)
    w(root, 'pubspec.yaml', pubspec('  hive_ce: ^2.10.0\n  hive_ce_flutter: ^2.2.0'))
    w(root, 'lib/core/di/injection.dart', core_injection('', ''))
    w(root, 'lib/app_injection.dart', app_injection(['orders']))
    w(root, 'lib/main.dart', main_dart(
        "import 'package:app/core/data/database/hive_boxes.dart';\n",
        '  registerAppDependencies(sl);\n  await initHive(sl);\n'))
    w(root, 'test/app_injection_test.dart', injection_test(CORE_TYPES, ORDERS_TYPES))
    w(root, 'lib/core/data/database/hive_boxes.dart', '''
import 'package:get_it/get_it.dart';
import 'package:hive_ce_flutter/hive_flutter.dart';

Future<void> initHive(GetIt sl) async {
  await Hive.initFlutter();
  final settingsBox = await Hive.openBox<Map>('settings');
  sl.registerSingleton<Box<Map>>(settingsBox, instanceName: 'settings');
}
''')
    w(root, 'lib/core/data/error_handling/hive_error_handler.dart', '''
import 'package:app/core/data/error_handling/failure.dart';

extension HiveFutureFailure<T> on Future<T> {
  Future<T> handleLocalFailure() async {
    try {
      return await this;
    } on Failure {
      rethrow;
    } catch (error, stackTrace) {
      throw LocalFailure.fromHive(error, stackTrace);
    }
  }
}

T handleLocalFailureSync<T>(T Function() op) {
  try {
    return op();
  } on Failure {
    rethrow;
  } catch (error, stackTrace) {
    throw LocalFailure.fromHive(error, stackTrace);
  }
}
''')


# ---------- app fixture: the drift project plus a clean `trips` feature, for tasks f1, f2, t1, g1, m2 ----------
APP_EN = '''{
  "orders": "Orders",
  "trips": "Trips",
  "retry": "Retry",
  "save": "Save",
  "somethingWentWrong": "Something went wrong",
  "fieldIsRequired": "This field is required",
  "enterValidEmail": "Enter a valid email address",
  "enterValidPhone": "Enter a valid phone number",
  "noInternetConnection": "No internet connection",
  "themeLight": "Light",
  "themeDark": "Dark"
}
'''
APP_AR = '''{
  "orders": "الطلبات",
  "trips": "الرحلات",
  "retry": "إعادة المحاولة",
  "save": "حفظ",
  "somethingWentWrong": "حدث خطأ ما",
  "fieldIsRequired": "هذا الحقل مطلوب",
  "enterValidEmail": "أدخل بريدًا إلكترونيًا صحيحًا",
  "enterValidPhone": "أدخل رقم هاتف صحيحًا",
  "noInternetConnection": "لا يوجد اتصال بالإنترنت",
  "themeLight": "فاتح",
  "themeDark": "داكن"
}
'''
APP_KEYS = ['orders', 'trips', 'retry', 'save', 'somethingWentWrong', 'fieldIsRequired', 'enterValidEmail',
            'enterValidPhone', 'noInternetConnection', 'themeLight', 'themeDark']
TRIPS = 'lib/feature/trips/'
TRIPS_SCREEN = TRIPS + 'presentation/trips_screen/'
TRIPS_TYPES = [('feature/trips/presentation/trips_screen/logic/trips_cubit.dart', 'TripsCubit'),
               ('feature/trips/data/repository/trips_repository.dart', 'TripsRepository'),
               ('feature/trips/data/data_source/trips_remote_data_source.dart', 'TripsRemoteDataSource')]
APP = {
    'lib/core/data/api/end_points.dart': '''
sealed class EndPoints {
  static const String baseUrl = 'https://api.example.com';

  static const String orders = '/orders';
  static const String trips = '/trips';
}
''',
    'lib/core/router/routes_strings.dart': '''
part of 'app_router.dart';

class RoutesStrings {
  RoutesStrings._();

  static const String orders = 'orders-screen';
  static const String trips = 'trips-screen';
}
''',
    'lib/core/router/app_router.dart': '''
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:app/core/di/injection.dart';
import 'package:app/feature/orders/presentation/orders_screen/ui/orders_screen.dart';
import 'package:app/feature/trips/presentation/trips_screen/logic/trips_cubit.dart';
import 'package:app/feature/trips/presentation/trips_screen/ui/trips_screen.dart';

part '../helpers/extensions/router_extensions.dart';
part 'routes_strings.dart';

sealed class AppRouter {
  static final GlobalKey<NavigatorState> navigationKey = GlobalKey<NavigatorState>();

  static final GlobalKey<ScaffoldMessengerState> scaffoldMessengerKey = GlobalKey<ScaffoldMessengerState>();

  static Route<dynamic>? generateRoute(RouteSettings settings) {
    switch (settings.name) {
      case RoutesStrings.orders:
        return MaterialPageRoute(builder: (_) => const OrdersScreen());
      case RoutesStrings.trips:
        return MaterialPageRoute(
          builder: (context) {
            return BlocProvider(
              create: (context) => sl<TripsCubit>(),
              child: const TripsScreen(),
            );
          },
        );
    }
    return MaterialPageRoute(
      builder: (context) => const Scaffold(body: Center(child: Text('No Route Found'))),
    );
  }
}
''',
    'lib/core/l10n/locale_keys.g.dart': locale_keys(APP_KEYS),
    'lib/core/helpers/app_form_validations.dart': r'''
import 'package:easy_localization/easy_localization.dart';
import 'package:app/core/l10n/locale_keys.g.dart';

sealed class AppFormValidations {
  static String? requiredField(String? value) =>
      (value == null || value.trim().isEmpty) ? LocaleKeys.fieldIsRequired.tr() : null;

  static String? email(String? value) =>
      (value == null || !RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(value.trim()))
          ? LocaleKeys.enterValidEmail.tr()
          : null;

  static String? phone(String? value) =>
      (value == null || !RegExp(r'^\+?[0-9]{8,15}$').hasMatch(value.trim()))
          ? LocaleKeys.enterValidPhone.tr()
          : null;
}
''',
    TRIPS + 'trips_injection.dart': '''
import 'package:get_it/get_it.dart';
import 'package:app/core/data/api/api_consumer.dart';
import 'package:app/core/services/network_status.dart';
import 'package:app/feature/trips/data/data_source/trips_remote_data_source.dart';
import 'package:app/feature/trips/data/repository/trips_repository.dart';
import 'package:app/feature/trips/presentation/trips_screen/logic/trips_cubit.dart';

void registerTripsDependencies(GetIt sl) {
  /// Blocs
  sl.registerFactory<TripsCubit>(() => TripsCubit(sl<TripsRepository>()));

  /// Repository
  sl.registerLazySingleton<TripsRepository>(
    () => TripsRepositoryImp(sl<TripsRemoteDataSource>(), sl<NetworkStatus>()),
  );

  /// Data Sources
  sl.registerLazySingleton<TripsRemoteDataSource>(
    () => TripsRemoteDataSourceImp(sl<ApiConsumer>()),
  );
}
''',
    TRIPS + 'data/model/trip_model.dart': '''
import 'package:equatable/equatable.dart';

class TripModel extends Equatable {
  final String? id;
  final String? title;
  final String? destination;
  final String? startDate;
  final double? price;
  final String? contactEmail;
  final String? contactPhone;

  const TripModel({
    this.id,
    this.title,
    this.destination,
    this.startDate,
    this.price,
    this.contactEmail,
    this.contactPhone,
  });

  factory TripModel.fromJson(Map<String, dynamic> json) => TripModel(
        id: json['id'] as String?,
        title: json['title'] as String?,
        destination: json['destination'] as String?,
        startDate: json['start_date'] as String?,
        price: (json['price'] as num?)?.toDouble(),
        contactEmail: json['contact_email'] as String?,
        contactPhone: json['contact_phone'] as String?,
      );

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'destination': destination,
        'start_date': startDate,
        'price': price,
        'contact_email': contactEmail,
        'contact_phone': contactPhone,
      };

  @override
  List<Object?> get props => [id, title, destination, startDate, price, contactEmail, contactPhone];
}
''',
    TRIPS + 'data/model/params/get_trips_params.dart': '''
import 'package:equatable/equatable.dart';

class GetTripsParams extends Equatable {
  final int page;

  const GetTripsParams({required this.page});

  Map<String, dynamic> toJson() => {'page': page};

  @override
  List<Object?> get props => [page];
}
''',
    TRIPS + 'data/data_source/trips_remote_data_source.dart': '''
import 'package:app/core/data/api/api_consumer.dart';
import 'package:app/core/data/api/end_points.dart';
import 'package:app/core/data/api/global_response.dart';
import 'package:app/feature/trips/data/model/params/get_trips_params.dart';
import 'package:app/feature/trips/data/model/trip_model.dart';

abstract class TripsRemoteDataSource {
  Future<GlobalResponse<List<TripModel>>> getTrips(GetTripsParams params);
}

class TripsRemoteDataSourceImp implements TripsRemoteDataSource {
  TripsRemoteDataSourceImp(this._apiConsumer);

  final ApiConsumer _apiConsumer;

  @override
  Future<GlobalResponse<List<TripModel>>> getTrips(GetTripsParams params) async {
    final response = await _apiConsumer.get(EndPoints.trips, queryParameters: params.toJson());
    return GlobalResponse.fromJson(
      response.data,
      fromJsonT: (json) => (json as List).map((trip) => TripModel.fromJson(trip)).toList(),
    );
  }
}
''',
    TRIPS + 'data/repository/trips_repository.dart': '''
import 'package:app/core/data/api/global_response.dart';
import 'package:app/core/data/error_handling/failure.dart';
import 'package:app/core/data/error_handling/result.dart';
import 'package:app/core/services/network_status.dart';
import 'package:app/feature/trips/data/data_source/trips_remote_data_source.dart';
import 'package:app/feature/trips/data/model/params/get_trips_params.dart';
import 'package:app/feature/trips/data/model/trip_model.dart';

abstract class TripsRepository {
  FutureResult<GlobalResponse<List<TripModel>>> getTrips(GetTripsParams params);
}

class TripsRepositoryImp implements TripsRepository {
  TripsRepositoryImp(this._remoteDataSource, this._network);

  final TripsRemoteDataSource _remoteDataSource;
  final NetworkStatus _network;

  @override
  FutureResult<GlobalResponse<List<TripModel>>> getTrips(GetTripsParams params) async {
    if (await _network.isConnected) {
      try {
        final result = await _remoteDataSource.getTrips(params);
        return Result.success(result);
      } on Failure catch (error) {
        return Result.failure(error);
      }
    }
    return Result.failure(ServerFailure.noNetwork());
  }
}
''',
    TRIPS_SCREEN + 'logic/trips_cubit.dart': '''
import 'package:equatable/equatable.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:app/core/data/error_handling/failure.dart';
import 'package:app/feature/trips/data/model/params/get_trips_params.dart';
import 'package:app/feature/trips/data/model/trip_model.dart';
import 'package:app/feature/trips/data/repository/trips_repository.dart';

part 'trips_state.dart';

class TripsCubit extends Cubit<TripsState> {
  TripsCubit(this._repository) : super(const TripsInitialState()) {
    getTrips();
  }

  final TripsRepository _repository;

  List<TripModel>? trips;

  Future<void> getTrips() async {
    emit(const GetTripsLoadingState());
    final result = await _repository.getTrips(const GetTripsParams(page: 1));
    result.when(
      onSuccess: (response) {
        trips = response.data;
        emit(const GetTripsSuccessState());
      },
      onFailure: (failure) => emit(GetTripsFailureState(failure: failure)),
    );
  }
}
''',
    TRIPS_SCREEN + 'logic/trips_state.dart': '''
part of 'trips_cubit.dart';

sealed class TripsState extends Equatable {
  const TripsState();

  @override
  List<Object?> get props => [];
}

final class TripsInitialState extends TripsState {
  const TripsInitialState();
}

final class GetTripsLoadingState extends TripsState {
  const GetTripsLoadingState();
}

final class GetTripsSuccessState extends TripsState {
  const GetTripsSuccessState();
}

final class GetTripsFailureState extends TripsState {
  const GetTripsFailureState({required this.failure});

  final Failure failure;

  @override
  List<Object?> get props => [failure];
}
''',
    TRIPS_SCREEN + 'ui/trips_screen.dart': '''
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:app/core/helpers/extensions/snackbar_extensions.dart';
import 'package:app/core/l10n/locale_keys.g.dart';
import 'package:app/core/widgets/layout/app_scaffold.dart';
import 'package:app/core/widgets/layout/global_appbar.dart';
import 'package:app/feature/trips/presentation/trips_screen/logic/trips_cubit.dart';
import 'package:app/feature/trips/presentation/trips_screen/ui/widgets/trips_body.dart';

class TripsScreen extends StatelessWidget {
  const TripsScreen({super.key});

  @override
  Widget build(BuildContext context) => BlocListener<TripsCubit, TripsState>(
        listener: (context, state) {
          if (state is GetTripsFailureState) {
            context.showErrorSnackBar(state.failure.message);
          }
        },
        child: AppScaffold(
          appBar: GlobalAppbar.main(titleText: LocaleKeys.trips.tr()),
          body: const TripsBody(),
        ),
      );
}
''',
    TRIPS_SCREEN + 'ui/widgets/trips_body.dart': '''
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:app/core/theme/app_tokens.dart';
import 'package:app/core/widgets/feedback/app_error_widget.dart';
import 'package:app/core/widgets/feedback/app_loader.dart';
import 'package:app/core/widgets/layout/space_widgets.dart';
import 'package:app/feature/trips/presentation/trips_screen/logic/trips_cubit.dart';
import 'package:app/feature/trips/presentation/trips_screen/ui/widgets/trip_item.dart';

class TripsBody extends StatelessWidget {
  const TripsBody({super.key});

  @override
  Widget build(BuildContext context) => BlocBuilder<TripsCubit, TripsState>(
        buildWhen: (previous, current) =>
            current is GetTripsLoadingState || current is GetTripsSuccessState || current is GetTripsFailureState,
        builder: (context, state) {
          final cubit = context.read<TripsCubit>();
          final tokens = context.tokens;
          return switch (state) {
            GetTripsFailureState(:final failure) => AppErrorWidget(message: failure.message, onRetry: cubit.getTrips),
            GetTripsSuccessState() => ListView.separated(
                padding: EdgeInsets.all(tokens.space.lg),
                itemCount: cubit.trips?.length ?? 0,
                separatorBuilder: (context, index) => VerticalSpace(tokens.space.md),
                itemBuilder: (context, index) => TripItem(
                  title: cubit.trips![index].title ?? '',
                  destination: cubit.trips![index].destination ?? '',
                  price: cubit.trips![index].price ?? 0,
                ),
              ),
            _ => const AppLoader(),
          };
        },
      );
}
''',
    TRIPS_SCREEN + 'ui/widgets/trip_item.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/app_tokens.dart';
import 'package:app/core/widgets/layout/app_container.dart';
import 'package:app/core/widgets/layout/space_widgets.dart';
import 'package:app/core/widgets/text/app_text.dart';

class TripItem extends StatelessWidget {
  const TripItem({super.key, required this.title, required this.destination, required this.price});

  final String title;
  final String destination;
  final double price;

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    return AppContainer(
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AppText(title, style: tokens.text.headingSm),
                AppText(destination, style: tokens.text.caption.copyWith(color: tokens.skin.textSecondary)),
              ],
            ),
          ),
          HorizontalSpace(tokens.space.md),
          AppText(
            '\\$${price.toStringAsFixed(2)}',
            style: tokens.text.labelMd.copyWith(color: tokens.skin.primary),
          ),
        ],
      ),
    );
  }
}
''',
    # legacy test for the legacy orders feature: flat test/ dir, mockito + codegen
    'test/orders_repository_test.dart': '''
import 'package:flutter_test/flutter_test.dart';
import 'package:mockito/annotations.dart';
import 'package:mockito/mockito.dart';
import 'package:app/feature/orders/data/data_source/orders_remote_data_source.dart';
import 'package:app/feature/orders/data/model/order_model.dart';
import 'package:app/feature/orders/data/repository/orders_repository.dart';

import 'orders_repository_test.mocks.dart';

@GenerateMocks([OrdersRemoteDataSource])
void main() {
  test('getOrders returns the orders from the data source', () async {
    final remote = MockOrdersRemoteDataSource();
    when(remote.getOrders()).thenAnswer((_) async => [OrderModel(id: '1', title: 'Order', total: 10)]);

    final orders = await OrdersRepository(remote).getOrders();

    expect(orders.length, 1);
  });
}
''',
}


def app(root):
    drift(root)
    for path, text in APP.items():
        w(root, path, text)
    w(root, 'assets/translations/en.json', APP_EN)
    w(root, 'assets/translations/ar.json', APP_AR)
    w(root, 'pubspec.yaml', pubspec(DRIFT_DEPS, DRIFT_DEV + '\n  mockito: ^5.4.4'))
    w(root, 'lib/app_injection.dart', app_injection(['orders', 'trips']))
    w(root, 'lib/my_app.dart', my_app('trips'))
    w(root, 'test/app_injection_test.dart', injection_test(DRIFT_CORE_TYPES, ORDERS_TYPES + TRIPS_TYPES))
    design = os.path.join(root, 'design')
    os.makedirs(design, exist_ok=True)
    shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fixture_files', 'design', 'prototype.html'), design)


# ---------- skin fixture: the app project with skins as a list (built-in + JSON), SkinCubit and AppMotion ----------
SKIN_DIR = 'lib/core/theme/skin/'


def json_skin_class():
    base = ''.join("\n  @override\n  Color get %s => base['%s']!;\n" % (s, s) for s in BASE_SLOTS)
    derived = ''.join("\n  @override\n  Color get %s => overrides['%s'] ?? super.%s;\n" % (s, s, s) for s in DERIVED_SLOTS)
    return '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/skin/app_skin.dart';

class JsonSkin extends AppSkin {
  const JsonSkin({
    required this.id,
    required this.themeMode,
    required this.names,
    required this.base,
    this.overrides = const {},
  });

  @override
  final String id;

  @override
  final ThemeMode themeMode;

  final Map<String, String> names;
  final Map<String, Color> base;
  final Map<String, Color> overrides;

  @override
  String displayName(Locale locale) => names[locale.languageCode] ?? names['en']!;
''' + base + derived + '}\n'


SKINS_README = '''# Skins

Every `*.json` file in this folder is a theme the user can pick. Drop a file in, rebuild the app, and it
appears in `SkinRegistry` — no Dart code. A file that breaks a rule below is skipped at launch.

| Field | Required | Rule |
|---|---|---|
| `id` | yes | `[a-z0-9_-]+`, unique, not `light` or `dark` (those are the built-ins) |
| `mode` | yes | `"light"` or `"dark"` |
| `name.en` | yes | the skin's name |
| `name.ar` | no | falls back to `name.en` |
| `colors` | yes | **every** base slot below, nothing else |
| `overrides` | no | any derived slot below, by name — replaces its formula |

Colours are `#RRGGBB` or `#AARRGGBB`. A dark skin must override `shadow`, `bottomSheetBackground` and
`dialogBackground`, like `DarkSkin` does.

## Base slots

''' + ', '.join('`%s`' % s for s in BASE_SLOTS) + '''

## Overridable derived slots

''' + ', '.join('`%s`' % s for s in DERIVED_SLOTS) + '\n'

SKIN = {
    'lib/core/data/cache/cache_keys.dart': '''
sealed class CacheKeys {
  static const String currentTheme = 'current-theme';
  static const String currentThemeMode = 'current-theme-mode';
  static const String accessToken = 'access-token';
}
''',
    'lib/core/data/cache/cache_helper.dart': '''
import 'package:shared_preferences/shared_preferences.dart';

export 'package:app/core/data/cache/cache_keys.dart';

sealed class CacheHelper {
  static late SharedPreferences _preferences;

  static Future<void> init() async => _preferences = await SharedPreferences.getInstance();

  static Object? get(String key) => _preferences.get(key);

  static Future<bool> save(String key, Object value) => switch (value) {
        String v => _preferences.setString(key, v),
        bool v => _preferences.setBool(key, v),
        int v => _preferences.setInt(key, v),
        double v => _preferences.setDouble(key, v),
        _ => throw ArgumentError('Unsupported cache value: $value'),
      };

  static Future<bool> remove(String key) => _preferences.remove(key);
}
''',
    'lib/core/theme/app_tokens.dart': app_tokens(True),
    SKIN_DIR + 'json_skin.dart': json_skin_class(),
    SKIN_DIR + 'loading/skin_source.dart': '''
import 'package:app/core/theme/skin/loading/skin_load_result.dart';

abstract interface class SkinSource {
  Future<List<SkinLoadResult>> load();
}
''',
    SKIN_DIR + 'loading/skin_load_result.dart': '''
import 'package:app/core/theme/skin/json_skin.dart';

sealed class SkinLoadResult {
  const SkinLoadResult({required this.origin});

  final String origin;
}

final class SkinLoaded extends SkinLoadResult {
  const SkinLoaded(this.skin, {required super.origin});

  final JsonSkin skin;
}

final class SkinRejected extends SkinLoadResult {
  const SkinRejected({required super.origin, required this.reason});

  final String reason;
}
''',
    SKIN_DIR + 'loading/skin_parser.dart': '''
import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:app/core/theme/skin/app_skin.dart';
import 'package:app/core/theme/skin/json_skin.dart';
import 'package:app/core/theme/skin/loading/skin_load_result.dart';

abstract final class SkinParser {
  static const reservedIds = {'light', 'dark'};

  static const _topLevelKeys = {'id', 'mode', 'name', 'colors', 'overrides'};

  static final _idPattern = RegExp(r'^[a-z0-9_-]+$');
  static final _colorPattern = RegExp(r'^#([0-9a-fA-F]{6}|[0-9a-fA-F]{8})$');

  static SkinLoadResult parse(String source, {required String origin}) {
    try {
      return SkinLoaded(_parse(source), origin: origin);
    } on _Rejection catch (rejection) {
      return SkinRejected(origin: origin, reason: rejection.reason);
    }
  }

  static JsonSkin _parse(String source) {
    final Object? decoded;
    try {
      decoded = jsonDecode(source);
    } on FormatException catch (error) {
      throw _Rejection('not valid JSON: ${error.message}');
    }
    final doc = _map(decoded, 'the file');
    for (final key in doc.keys) {
      if (!_topLevelKeys.contains(key)) throw _Rejection('unknown key "$key"');
    }
    return JsonSkin(
      id: _id(doc['id']),
      themeMode: _mode(doc['mode']),
      names: _names(doc['name']),
      base: _colors(doc['colors']),
      overrides: _overrides(doc['overrides']),
    );
  }

  static String _id(Object? value) {
    if (value is! String || !_idPattern.hasMatch(value)) {
      throw const _Rejection('id must be a non-empty [a-z0-9_-] string');
    }
    if (reservedIds.contains(value)) throw _Rejection('id "$value" is reserved for a built-in skin');
    return value;
  }

  static ThemeMode _mode(Object? value) => switch (value) {
        'light' => ThemeMode.light,
        'dark' => ThemeMode.dark,
        _ => throw const _Rejection('mode must be "light" or "dark"'),
      };

  static Map<String, String> _names(Object? value) {
    final name = _map(value, 'name');
    final en = name['en'];
    if (en is! String || en.trim().isEmpty) throw const _Rejection('name.en must be a non-empty string');
    final ar = name['ar'];
    return {'en': en, if (ar is String && ar.trim().isNotEmpty) 'ar': ar};
  }

  static Map<String, Color> _colors(Object? value) {
    final colors = _map(value, 'colors');
    for (final key in colors.keys) {
      if (!AppSkin.baseSlotNames.contains(key)) throw _Rejection('colors.$key is not a base slot');
    }
    return {
      for (final slot in AppSkin.baseSlotNames)
        slot: colors.containsKey(slot) ? _color(colors[slot], 'colors.$slot') : throw _Rejection('colors.$slot is missing'),
    };
  }

  static Map<String, Color> _overrides(Object? value) {
    if (value == null) return const {};
    final overrides = _map(value, 'overrides');
    return {
      for (final entry in overrides.entries)
        entry.key: AppSkin.derivedSlotNames.contains(entry.key)
            ? _color(entry.value, 'overrides.${entry.key}')
            : throw _Rejection('overrides.${entry.key} is not a derived slot'),
    };
  }

  static Color _color(Object? value, String field) {
    if (value is! String || !_colorPattern.hasMatch(value)) throw _Rejection('$field must be #RRGGBB or #AARRGGBB');
    final hex = value.substring(1);
    return Color(int.parse(hex.length == 6 ? 'FF$hex' : hex, radix: 16));
  }

  static Map<String, dynamic> _map(Object? value, String field) {
    if (value is! Map<String, dynamic>) throw _Rejection('$field must be a JSON object');
    return value;
  }
}

final class _Rejection implements Exception {
  const _Rejection(this.reason);

  final String reason;
}
''',
    SKIN_DIR + 'loading/asset_skin_source.dart': '''
import 'package:flutter/services.dart';
import 'package:app/core/theme/skin/loading/skin_load_result.dart';
import 'package:app/core/theme/skin/loading/skin_parser.dart';
import 'package:app/core/theme/skin/loading/skin_source.dart';

class AssetSkinSource implements SkinSource {
  AssetSkinSource({AssetBundle? bundle}) : _bundle = bundle ?? rootBundle;

  static const folder = 'assets/skins/';

  final AssetBundle _bundle;

  @override
  Future<List<SkinLoadResult>> load() async {
    final manifest = await AssetManifest.loadFromAssetBundle(_bundle);
    final paths = manifest.listAssets().where((path) => path.startsWith(folder) && path.endsWith('.json')).toList()
      ..sort();
    return [for (final path in paths) await _read(path)];
  }

  Future<SkinLoadResult> _read(String path) async {
    try {
      return SkinParser.parse(await _bundle.loadString(path), origin: path);
    } catch (error) {
      return SkinRejected(origin: path, reason: 'unreadable: $error');
    }
  }
}
''',
    SKIN_DIR + 'loading/skin_registry.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/skin/app_skin.dart';
import 'package:app/core/theme/skin/dark_skin.dart';
import 'package:app/core/theme/skin/light_skin.dart';
import 'package:app/core/theme/skin/loading/skin_load_result.dart';
import 'package:app/core/theme/skin/loading/skin_source.dart';

class SkinRegistry {
  SkinRegistry({this.sources = const []});

  static const builtIns = <AppSkin>[LightSkin(), DarkSkin()];

  final List<SkinSource> sources;
  final List<AppSkin> _loaded = [];
  final List<SkinRejected> rejected = [];

  List<AppSkin> get skins => [...builtIns, ..._loaded];

  AppSkin? byId(String id) {
    for (final skin in skins) {
      if (skin.id == id) return skin;
    }
    return null;
  }

  AppSkin builtInFor(ThemeMode mode) => mode == ThemeMode.dark ? const DarkSkin() : const LightSkin();

  Future<void> load() async {
    final loaded = <AppSkin>[];
    final taken = {for (final skin in builtIns) skin.id};
    rejected.clear();
    for (final source in sources) {
      for (final result in await source.load()) {
        switch (result) {
          case SkinRejected rejection:
            rejected.add(rejection);
          case SkinLoaded(:final skin, :final origin):
            if (taken.add(skin.id)) {
              loaded.add(skin);
            } else {
              rejected.add(SkinRejected(origin: origin, reason: 'id "${skin.id}" is taken'));
            }
        }
      }
    }
    _loaded
      ..clear()
      ..addAll(loaded);
  }
}
''',
    SKIN_DIR + 'logic/skin_cubit.dart': '''
import 'package:equatable/equatable.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:app/core/data/cache/cache_helper.dart';
import 'package:app/core/theme/skin/app_skin.dart';
import 'package:app/core/theme/skin/loading/skin_registry.dart';

part 'skin_state.dart';

class SkinCubit extends Cubit<SkinState> {
  SkinCubit(this._registry) : skin = _restore(_registry), super(const SkinInitialState());

  final SkinRegistry _registry;

  AppSkin skin;

  List<AppSkin> get skins => _registry.skins;

  static AppSkin _restore(SkinRegistry registry) {
    final id = CacheHelper.get(CacheKeys.currentTheme);
    final saved = id is String ? registry.byId(id) : null;
    if (saved != null) return saved;
    final mode = CacheHelper.get(CacheKeys.currentThemeMode) == ThemeMode.dark.name ? ThemeMode.dark : ThemeMode.light;
    return registry.builtInFor(mode);
  }

  void select(AppSkin newSkin) {
    if (newSkin == skin) return;
    skin = newSkin;
    CacheHelper.save(CacheKeys.currentTheme, newSkin.id);
    CacheHelper.save(CacheKeys.currentThemeMode, newSkin.themeMode.name);
    emit(SkinChangedState(newSkin));
  }
}

extension SkinSwitcherContext on BuildContext {
  void selectSkin(AppSkin skin) => read<SkinCubit>().select(skin);
}
''',
    SKIN_DIR + 'logic/skin_state.dart': '''
part of 'skin_cubit.dart';

sealed class SkinState extends Equatable {
  const SkinState();

  @override
  List<Object?> get props => [];
}

final class SkinInitialState extends SkinState {
  const SkinInitialState();
}

final class SkinChangedState extends SkinState {
  const SkinChangedState(this.skin);

  final AppSkin skin;

  @override
  List<Object?> get props => [skin];
}
''',
    'lib/core/theme/motion/app_motion.dart': '''
import 'package:flutter/animation.dart';
import 'package:flutter/foundation.dart';
import 'package:motor/motor.dart';

/// Motion tokens mirroring the design's durations, easing curves, and
/// animation distances. Every animated widget picks from here instead of
/// inventing its own timing.
@immutable
class AppMotion {
  const AppMotion();

  static const standard = AppMotion();

  /// Micro interactions: press states, border and color flips on chips
  /// and inputs. Example: a filter chip's border darkening on tap.
  Duration get fast => const Duration(milliseconds: 120);

  /// Standard transitions: fades, background shifts, tab label color.
  /// Example: the primary button fading when it is disabled.
  Duration get base => const Duration(milliseconds: 180);

  /// Entrances of content blocks. Example: a trip card appearing.
  Duration get slow => const Duration(milliseconds: 260);

  /// Big springy morphs. Example: a segmented thumb sliding between
  /// filters.
  Duration get emphasis => const Duration(milliseconds: 450);

  /// One full sweep of the loading shimmer across a placeholder card.
  Duration get shimmerLoop => const Duration(milliseconds: 1400);

  /// The default deceleration curve: fast start, gentle stop. Pairs with
  /// [fast]/[base] for most transitions.
  Curve get easeOut => const Cubic(0.22, 0.61, 0.36, 1);

  /// The symmetric curve for looping animations. Pairs with
  /// [shimmerLoop].
  Curve get easeInOut => const Cubic(0.65, 0, 0.35, 1);

  /// The overshoot curve giving entrances a playful bounce. Pairs with
  /// [slow]/[emphasis] for pops and sheets.
  Curve get spring => const Cubic(0.34, 1.4, 0.64, 1);

  /// How far a fade-up entrance starts below its resting spot. Example:
  /// a form's fields rising 10 into place.
  double get fadeUpOffset => 10;

  /// How far a sheet-like entrance starts below its resting spot.
  /// Example: the filter sheet rising 60 into place.
  double get slideUpOffset => 60;

  /// The starting scale of a pop entrance. Example: an empty-state
  /// illustration scaling from 0.94 to full size.
  double get popScale => 0.94;

  /// The delay before the first item of a staggered group starts.
  Duration get staggerBase => const Duration(milliseconds: 120);

  /// The gap between consecutive items of a staggered group. Example: the
  /// offset between cards popping in on a list.
  Duration get staggerStep => const Duration(milliseconds: 40);

  /// The entrance delay for item [index] of a staggered group. Pass
  /// `leadIn: false` for a list the user is already looking at.
  Duration staggerAt(int index, {bool leadIn = true}) =>
      (leadIn ? staggerBase : Duration.zero) + staggerStep * index;

  /// Small components reacting to touch: chips, buttons, cards. Example:
  /// a card's press morph.
  Motion get pressSpring => const MaterialSpringMotion.expressiveSpatialFast();

  /// Large surfaces entering. Example: a bottom sheet springing up.
  Motion get surfaceSpring => const MaterialSpringMotion.expressiveSpatialDefault();

  /// Exits and dismissals: quieter, so the overshoot doesn't fight the
  /// gesture that dismissed it. Example: a sheet flung closed.
  Motion get exitSpring => const MaterialSpringMotion.standardSpatialFast();

  /// Non-spatial changes: color, opacity, elevation. Example: a selection
  /// tint settling after a tap.
  Motion get effectsSpring => const MaterialSpringMotion.standardEffectsDefault();
}
''',
    'lib/core/theme/motion/spring_page_physics.dart': '''
import 'package:flutter/material.dart';
import 'package:motor/motor.dart';

class SpringPagePhysics extends PageScrollPhysics {
  const SpringPagePhysics({super.parent});

  @override
  SpringPagePhysics applyTo(ScrollPhysics? ancestor) => SpringPagePhysics(parent: buildParent(ancestor));

  @override
  SpringDescription get spring => const MaterialSpringMotion.standardSpatialDefault().description;
}
''',
    'lib/core/widgets/buttons/primary_button.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/theme/app_tokens.dart';
import 'package:app/core/widgets/feedback/app_loader.dart';
import 'package:app/core/widgets/text/app_text.dart';

class PrimaryButton extends StatelessWidget {
  const PrimaryButton({super.key, required this.text, required this.onPressed, this.isLoading = false, this.backgroundColor})
      : expand = false;

  const PrimaryButton.expand({super.key, required this.text, required this.onPressed, this.isLoading = false, this.backgroundColor})
      : expand = true;

  final String text;
  final VoidCallback? onPressed;
  final bool isLoading;
  final bool expand;
  final Color? backgroundColor;

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    final button = ElevatedButton(
      style: ElevatedButton.styleFrom(
        backgroundColor: backgroundColor ?? tokens.skin.buttonBackground,
        shape: RoundedRectangleBorder(borderRadius: tokens.radius.button),
      ),
      onPressed: isLoading ? null : onPressed,
      child: isLoading
          ? const AppLoader(size: 18)
          : AppText(text, style: tokens.text.labelMd.copyWith(color: tokens.skin.buttonText)),
    );
    final faded = AnimatedOpacity(
      duration: tokens.motion.base,
      curve: tokens.motion.easeOut,
      opacity: onPressed == null ? 0.6 : 1,
      child: button,
    );
    return expand ? SizedBox(width: double.infinity, child: faded) : faded;
  }
}
''',
    'lib/my_app.dart': '''
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:app/core/di/injection.dart';
import 'package:app/core/router/app_router.dart';
import 'package:app/core/theme/app_theme.dart';
import 'package:app/core/theme/skin/loading/skin_registry.dart';
import 'package:app/core/theme/skin/logic/skin_cubit.dart';

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiBlocProvider(
      providers: [BlocProvider(create: (context) => SkinCubit(sl<SkinRegistry>()))],
      child: BlocBuilder<SkinCubit, SkinState>(
        buildWhen: (previous, current) => current is SkinChangedState,
        builder: (context, state) {
          final skin = context.read<SkinCubit>().skin;
          return ScreenUtilInit(
            designSize: const Size(375, 812),
            minTextAdapt: true,
            builder: (context, child) => MaterialApp(
              debugShowCheckedModeBanner: false,
              navigatorKey: AppRouter.navigationKey,
              scaffoldMessengerKey: AppRouter.scaffoldMessengerKey,
              theme: AppTheme.of(skin),
              localizationsDelegates: context.localizationDelegates,
              supportedLocales: context.supportedLocales,
              locale: context.locale,
              onGenerateRoute: AppRouter.generateRoute,
              initialRoute: RoutesStrings.trips,
            ),
          );
        },
      ),
    );
  }
}
''',
    'assets/skins/ocean.json': json_skin_file('ocean', 'dark', 'Ocean', 'المحيط', OCEAN, OCEAN_OVERRIDES),
    'assets/skins/README.md': SKINS_README,
}


def skin(root):
    app(root)
    shutil.rmtree(os.path.join(root, 'design'))
    for path, text in SKIN.items():
        w(root, path, text)
    w(root, 'lib/core/di/injection.dart', core_injection(
        DRIFT_CORE_IMPORTS + "import 'package:app/core/theme/skin/loading/asset_skin_source.dart';\n"
        "import 'package:app/core/theme/skin/loading/skin_registry.dart';\n" + DRIFT_CORE_FEATURE_IMPORT,
        DRIFT_CORE_BODY.replace('\n  // budget', '''
  /// Theme
  sl.registerLazySingleton<SkinRegistry>(() => SkinRegistry(sources: [AssetSkinSource()]));

  // budget''')))
    w(root, 'lib/main.dart', main_dart(
        "import 'package:app/core/data/cache/cache_helper.dart';\n"
        "import 'package:app/core/theme/skin/loading/skin_registry.dart';\n",
        '  await CacheHelper.init();\n  registerAppDependencies(sl);\n  await sl<SkinRegistry>().load();\n'))
    w(root, 'test/app_injection_test.dart', injection_test(
        DRIFT_CORE_TYPES + [('core/theme/skin/loading/skin_registry.dart', 'SkinRegistry')], ORDERS_TYPES + TRIPS_TYPES))
    w(root, 'pubspec.yaml', pubspec(
        DRIFT_DEPS + '\n  shared_preferences: ^2.3.2\n  motor: ^1.1.0',
        DRIFT_DEV + '\n  mockito: ^5.4.4', '    - assets/skins/\n'))


# ---------- older fixture: the app project on the pre-2.0 theme (AppColors + AppTextStyle, no AppTokens) ----------
OLDER = {
    'lib/core/app_themes/colors/app_colors.dart': '''
import 'package:flutter/material.dart';

sealed class AppColors {
  static const Color primary = Color(0xFF1E6FD9);
  static const Color background = Color(0xFFF7F8FA);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color textPrimary = Color(0xFF1A1C1E);
  static const Color textSecondary = Color(0xFF6B7280);
  static const Color success = Color(0xFF16A34A);
  static const Color warning = Color(0xFFF59E0B);
  static const Color error = Color(0xFFDC2626);
  static const Color divider = Color(0xFFE5E7EB);
}
''',
    'lib/core/app_themes/text_style/app_text_style.dart': '''
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:app/core/app_themes/colors/app_colors.dart';

sealed class AppTextStyle {
  static TextStyle get style12Regular =>
      TextStyle(fontSize: 12.sp, fontWeight: FontWeight.w400, color: AppColors.textSecondary);
  static TextStyle get style14Regular =>
      TextStyle(fontSize: 14.sp, fontWeight: FontWeight.w400, color: AppColors.textPrimary);
  static TextStyle get style14Medium =>
      TextStyle(fontSize: 14.sp, fontWeight: FontWeight.w500, color: AppColors.textPrimary);
  static TextStyle get style16Medium =>
      TextStyle(fontSize: 16.sp, fontWeight: FontWeight.w500, color: AppColors.textPrimary);
  static TextStyle get style18Bold =>
      TextStyle(fontSize: 18.sp, fontWeight: FontWeight.w700, color: AppColors.textPrimary);
}
''',
    'lib/core/widgets/text/app_text.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/app_themes/text_style/app_text_style.dart';

class AppText extends StatelessWidget {
  const AppText(this.text, {super.key, this.style, this.maxLines, this.textAlign});

  final String text;
  final TextStyle? style;
  final int? maxLines;
  final TextAlign? textAlign;

  @override
  Widget build(BuildContext context) => Text(
        text,
        style: style ?? AppTextStyle.style14Regular,
        maxLines: maxLines,
        overflow: maxLines == null ? null : TextOverflow.ellipsis,
        textAlign: textAlign,
      );
}
''',
    'lib/core/widgets/text/bullet_text.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/app_themes/text_style/app_text_style.dart';
import 'package:app/core/widgets/layout/space_widgets.dart';
import 'package:app/core/widgets/text/app_text.dart';

class BulletText extends StatelessWidget {
  const BulletText(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) => Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          AppText('•', style: AppTextStyle.style14Regular),
          const HorizontalSpace(8),
          Expanded(child: AppText(text, maxLines: 3)),
        ],
      );
}
''',
    'lib/core/widgets/layout/app_scaffold.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/app_themes/colors/app_colors.dart';

class AppScaffold extends StatelessWidget {
  const AppScaffold({
    super.key,
    required this.body,
    this.appBar,
    this.floatingActionButton,
    this.bottomNavigationBar,
  });

  final Widget body;
  final PreferredSizeWidget? appBar;
  final Widget? floatingActionButton;
  final Widget? bottomNavigationBar;

  @override
  Widget build(BuildContext context) => Scaffold(
        backgroundColor: AppColors.background,
        appBar: appBar,
        body: SafeArea(child: body),
        floatingActionButton: floatingActionButton,
        bottomNavigationBar: bottomNavigationBar,
      );
}
''',
    'lib/core/widgets/layout/global_appbar.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/app_themes/colors/app_colors.dart';
import 'package:app/core/app_themes/text_style/app_text_style.dart';

class GlobalAppbar extends StatelessWidget implements PreferredSizeWidget {
  const GlobalAppbar.main({super.key, required this.titleText, this.actions}) : showBack = false;

  const GlobalAppbar.sub({super.key, required this.titleText, this.actions}) : showBack = true;

  final String titleText;
  final List<Widget>? actions;
  final bool showBack;

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) => AppBar(
        backgroundColor: AppColors.surface,
        automaticallyImplyLeading: showBack,
        title: Text(titleText, style: AppTextStyle.style18Bold),
        actions: actions,
      );
}
''',
    'lib/core/widgets/layout/app_container.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/app_themes/colors/app_colors.dart';

class AppContainer extends StatelessWidget {
  const AppContainer({super.key, required this.child, this.padding = const EdgeInsets.all(12)});

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => Container(
        padding: padding,
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.divider),
        ),
        child: child,
      );
}
''',
    'lib/core/widgets/buttons/primary_button.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/app_themes/colors/app_colors.dart';
import 'package:app/core/widgets/feedback/app_loader.dart';
import 'package:app/core/widgets/text/app_text.dart';

class PrimaryButton extends StatelessWidget {
  const PrimaryButton({super.key, required this.text, required this.onPressed, this.isLoading = false})
      : expand = false;

  const PrimaryButton.expand({super.key, required this.text, required this.onPressed, this.isLoading = false})
      : expand = true;

  final String text;
  final VoidCallback? onPressed;
  final bool isLoading;
  final bool expand;

  @override
  Widget build(BuildContext context) {
    final button = ElevatedButton(
      style: ElevatedButton.styleFrom(backgroundColor: AppColors.primary),
      onPressed: isLoading ? null : onPressed,
      child: isLoading ? const AppLoader(size: 18) : AppText(text),
    );
    return expand ? SizedBox(width: double.infinity, child: button) : button;
  }
}
''',
    'lib/core/widgets/buttons/secondary_button.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/app_themes/colors/app_colors.dart';
import 'package:app/core/app_themes/text_style/app_text_style.dart';
import 'package:app/core/widgets/text/app_text.dart';

class SecondaryButton extends StatelessWidget {
  const SecondaryButton({super.key, required this.text, required this.onPressed});

  final String text;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) => OutlinedButton(
        style: OutlinedButton.styleFrom(side: const BorderSide(color: AppColors.primary)),
        onPressed: onPressed,
        child: AppText(text, style: AppTextStyle.style14Medium.copyWith(color: AppColors.primary)),
      );
}
''',
    'lib/core/widgets/inputs/app_text_field.dart': '''
import 'package:flutter/material.dart';

class AppTextField extends StatelessWidget {
  const AppTextField({
    super.key,
    this.controller,
    this.hintText,
    this.validator,
    this.maxLines = 1,
    this.keyboardType,
  });

  final TextEditingController? controller;
  final String? hintText;
  final String? Function(String?)? validator;
  final int maxLines;
  final TextInputType? keyboardType;

  @override
  Widget build(BuildContext context) => TextFormField(
        controller: controller,
        validator: validator,
        maxLines: maxLines,
        keyboardType: keyboardType,
        decoration: InputDecoration(hintText: hintText, border: const OutlineInputBorder()),
      );
}
''',
    'lib/core/widgets/inputs/app_check_box.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/app_themes/colors/app_colors.dart';

class AppCheckBox extends StatelessWidget {
  const AppCheckBox({super.key, required this.value, required this.onChanged});

  final bool value;
  final ValueChanged<bool?>? onChanged;

  @override
  Widget build(BuildContext context) => Checkbox(value: value, onChanged: onChanged, activeColor: AppColors.primary);
}
''',
    'lib/core/widgets/feedback/app_loader.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/app_themes/colors/app_colors.dart';

class AppLoader extends StatelessWidget {
  const AppLoader({super.key, this.size = 32});

  final double size;

  @override
  Widget build(BuildContext context) => Center(
        child: SizedBox.square(
          dimension: size,
          child: const CircularProgressIndicator(color: AppColors.primary),
        ),
      );
}
''',
    'lib/core/widgets/feedback/app_error_widget.dart': '''
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:app/core/l10n/locale_keys.g.dart';
import 'package:app/core/widgets/buttons/primary_button.dart';
import 'package:app/core/widgets/layout/space_widgets.dart';
import 'package:app/core/widgets/text/app_text.dart';

class AppErrorWidget extends StatelessWidget {
  const AppErrorWidget({super.key, required this.message, this.onRetry});

  final String message;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) => Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            AppText(message, textAlign: TextAlign.center),
            if (onRetry != null) ...[
              const VerticalSpace(12),
              PrimaryButton(text: LocaleKeys.retry.tr(), onPressed: onRetry),
            ],
          ],
        ),
      );
}
''',
    'lib/core/helpers/extensions/snackbar_extensions.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/app_themes/colors/app_colors.dart';
import 'package:app/core/widgets/text/app_text.dart';

extension ShowSnackbarExtension on BuildContext {
  void showSnackBar(String message) => _show(message, AppColors.success);

  void showErrorSnackBar(String message) => _show(message, AppColors.error);

  void _show(String message, Color background) {
    ScaffoldMessenger.of(this).showSnackBar(
      SnackBar(content: AppText(message), backgroundColor: background),
    );
  }
}
''',
    'lib/my_app.dart': '''
import 'package:easy_localization/easy_localization.dart';
import 'package:flutter/material.dart';
import 'package:flutter_screenutil/flutter_screenutil.dart';
import 'package:app/core/app_themes/colors/app_colors.dart';
import 'package:app/core/router/app_router.dart';

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ScreenUtilInit(
      designSize: const Size(375, 812),
      minTextAdapt: true,
      builder: (context, child) => MaterialApp(
        debugShowCheckedModeBanner: false,
        navigatorKey: AppRouter.navigationKey,
        scaffoldMessengerKey: AppRouter.scaffoldMessengerKey,
        theme: ThemeData(
          useMaterial3: true,
          scaffoldBackgroundColor: AppColors.background,
          colorScheme: ColorScheme.fromSeed(seedColor: AppColors.primary),
        ),
        localizationsDelegates: context.localizationDelegates,
        supportedLocales: context.supportedLocales,
        locale: context.locale,
        onGenerateRoute: AppRouter.generateRoute,
        initialRoute: RoutesStrings.trips,
      ),
    );
  }
}
''',
    TRIPS_SCREEN + 'ui/widgets/trips_body.dart': '''
import 'package:flutter/material.dart';
import 'package:flutter_bloc/flutter_bloc.dart';
import 'package:app/core/widgets/feedback/app_error_widget.dart';
import 'package:app/core/widgets/feedback/app_loader.dart';
import 'package:app/core/widgets/layout/space_widgets.dart';
import 'package:app/feature/trips/presentation/trips_screen/logic/trips_cubit.dart';
import 'package:app/feature/trips/presentation/trips_screen/ui/widgets/trip_item.dart';

class TripsBody extends StatelessWidget {
  const TripsBody({super.key});

  @override
  Widget build(BuildContext context) => BlocBuilder<TripsCubit, TripsState>(
        buildWhen: (previous, current) =>
            current is GetTripsLoadingState || current is GetTripsSuccessState || current is GetTripsFailureState,
        builder: (context, state) {
          final cubit = context.read<TripsCubit>();
          return switch (state) {
            GetTripsFailureState(:final failure) => AppErrorWidget(message: failure.message, onRetry: cubit.getTrips),
            GetTripsSuccessState() => ListView.separated(
                padding: const EdgeInsets.all(16),
                itemCount: cubit.trips?.length ?? 0,
                separatorBuilder: (context, index) => const VerticalSpace(12),
                itemBuilder: (context, index) => TripItem(
                  title: cubit.trips![index].title ?? '',
                  destination: cubit.trips![index].destination ?? '',
                  price: cubit.trips![index].price ?? 0,
                ),
              ),
            _ => const AppLoader(),
          };
        },
      );
}
''',
    TRIPS_SCREEN + 'ui/widgets/trip_item.dart': '''
import 'package:flutter/material.dart';
import 'package:app/core/app_themes/colors/app_colors.dart';
import 'package:app/core/app_themes/text_style/app_text_style.dart';
import 'package:app/core/widgets/layout/app_container.dart';
import 'package:app/core/widgets/layout/space_widgets.dart';
import 'package:app/core/widgets/text/app_text.dart';

class TripItem extends StatelessWidget {
  const TripItem({super.key, required this.title, required this.destination, required this.price});

  final String title;
  final String destination;
  final double price;

  @override
  Widget build(BuildContext context) => AppContainer(
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  AppText(title, style: AppTextStyle.style16Medium),
                  AppText(destination, style: AppTextStyle.style12Regular),
                ],
              ),
            ),
            const HorizontalSpace(12),
            AppText(
              '\\$${price.toStringAsFixed(2)}',
              style: AppTextStyle.style14Medium.copyWith(color: AppColors.primary),
            ),
          ],
        ),
      );
}
''',
}


def older(root):
    app(root)
    shutil.rmtree(os.path.join(root, 'lib/core/theme'))
    shutil.rmtree(os.path.join(root, 'design'))
    for path, text in OLDER.items():
        w(root, path, text)


def nowrap(src, dst):
    shutil.copytree(src, dst)
    for name in NOWRAP_REMOVED:
        os.remove(os.path.join(dst, 'lib/core/widgets', name + '.dart'))


if __name__ == '__main__':
    for engine, build in (('drift', drift), ('hive', hive), ('app', app), ('skin', skin), ('older', older)):
        root = os.path.join(OUT, 'fixture-' + engine)
        for d in (root, root + '-nowrap'):
            shutil.rmtree(d, ignore_errors=True)
        build(root)
        nowrap(root, root + '-nowrap')
    print('fixtures written to', OUT)
