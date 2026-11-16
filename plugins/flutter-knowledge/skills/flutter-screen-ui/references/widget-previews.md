# Widget previews

Flutter Widget Previewer (`package:flutter/widget_previews.dart`), only when the user asks. They suit presentational widgets that take everything through constructor parameters: section widgets, rows, cards and core wrappers. A Screen or Body that reads a cubit, `sl`, the cache or a native plugin does not preview (the previewer runs on the web); preview its section widgets instead. Previews live in a sibling file named after the widget, `order_summary_card_preview.dart` next to `order_summary_card.dart`, holding only top-level `@AppPreview` functions with sample values, so the widget file keeps one class and no preview code. Every preview goes through one shared annotation that applies the app theme:

```dart
final class AppPreview extends Preview {
  const AppPreview({
    super.group,
    super.name,
    super.size,
    super.textScaleFactor,
    super.brightness,
  }) : super(wrapper: appPreviewWrapper);
}

Widget appPreviewWrapper(Widget child) {
  return MaterialApp(
    debugShowCheckedModeBanner: false,
    theme: AppTheme.light,
    home: Material(child: child),
  );
}
```

It lives in `lib/core/helpers/app_preview.dart`; mirror the project's widget-test wrapper inside `appPreviewWrapper` (its `ScreenUtilInit` and design size) so `context.tokens` resolves. `group` is the feature or core folder; add a large-text variant (`textScaleFactor: 2`) where the widget has text. A widget that reads `LocaleKeys` shows its keys unless the wrapper also initializes the configured localization. Open them with `flutter widget-preview start` or the IDE's Widget Preview panel. Previews are a development aid, not design evidence: visual fidelity is still proven by `visual-verification` and goldens.
