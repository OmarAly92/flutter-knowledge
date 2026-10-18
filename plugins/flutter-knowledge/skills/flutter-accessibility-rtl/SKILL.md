---
name: flutter-accessibility-rtl
description: Use before changing Flutter controls, semantics, focus, touch targets, directional icons/layout, localization behavior or text scaling; also accessibility and Arabic/RTL reviews.
---

# Accessibility and RTL

Read the [configuration contract](../flutter-init/references/configuration.md). Keep `flutter-screen-ui`'s wrappers, Screen/Body split, tokens and configured localization. Accessibility is a UI responsibility regardless of the package stack.

## Implement the interaction, not only its appearance

- Give icon-only actions a localized semantic label and tooltip through the existing core widget API. Check existing semantics before wrapping: do not announce the same label twice. Decorative images should not become interactive or announce asset filenames.
- Describe loading, error, selection and disabled states through the appropriate semantics; keep announcements meaningful rather than announcing every animation frame. Navigation/snackbar effects remain in the Screen listener, never the owner or a build branch.
- Preserve keyboard focus order and activation on desktop/web. Reuse the core control's focus behavior before adding custom handlers.

## Direction and text

Use directional insets, alignment, positions and corner APIs for logical start/end relationships. Physical coordinates remain valid for measured geometry and non-mirroring artwork; do not mechanically flip every left/right value. Mirror navigation arrows and directional actions when appropriate; preserve logos and media symbols. Let locale-derived Directionality flow from the app root.

Reuse the project's `BuildContext` direction extension for boolean checks: `context.isRtl` / `context.isLtr`. Extend its existing locale/context helper when present; otherwise place a focused helper in `lib/core/l10n/locale_extensions.dart`. Getters read the current subtree's `Directionality`, not the locale's language code or `isArabic`, so explicit direction overrides and other RTL languages remain correct. Prefer directional layout APIs when no boolean branch is needed.

```dart
extension LocaleContext on BuildContext {
  bool get isRtl => Directionality.of(this) == TextDirection.rtl;

  bool get isLtr => Directionality.of(this) == TextDirection.ltr;
}
```

The helper imports Flutter widgets. If its existing localization import also exports `TextDirection`, hide that symbol from the localization import so these getters use Flutter's type.

Exercise real Arabic mixed with numbers, email and Latin names. Keep translation completeness and generated accessors under `add-translation`; semantics labels are user-facing text too.

Respect the user's TextScaler. Do not globally disable or clamp scaling to rescue layout. Text-bearing controls must grow or scroll appropriately; do not fix clipping with smaller fonts or truncate essential errors, balances or actions. Invoke `flutter-responsive-layout` for constraint/overflow work.

## Verification

Use the project's supported target sizes and theme-level contrast checks. Flutter documents Android 48×48 dp and iOS 44×44 pt minimum target guidance, with 4.5:1 small-text and 3:1 large-text contrast. Keep these values in the appropriate core component/design system; do not scatter literals through features. [Flutter guidance](https://docs.flutter.dev/ui/accessibility/ui-design-and-styling).

In existing or explicitly requested widget tests, enable semantics and use the guideline checks for target labels, size and contrast. Under the design golden workflow, include the existing Arabic/large-text variants; add a focused Arabic + large-text + narrow-container case when the changed layout makes their interaction relevant. Do not generate unrelated unit suites. [Testing APIs](https://docs.flutter.dev/ui/accessibility/accessibility-testing).

Runtime screen-reader inspection requires the project's permission to run the app. Report that check as not performed when unavailable; a golden does not prove screen-reader behavior.
