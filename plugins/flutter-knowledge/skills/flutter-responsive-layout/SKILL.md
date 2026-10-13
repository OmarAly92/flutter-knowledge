---
name: flutter-responsive-layout
description: Use before Flutter layout work involving constraints, overflow, keyboard insets, small screens, large text, split panes, tablet/desktop targets or breakpoints, including screens built from a single design artboard.
---

# Responsive layout

Read the [configuration contract](../flutter-init/references/configuration.md) and the project's `lib/core/layout/` helpers. Keep Screen/Body composition, tokens and core wrappers. Package selection does not authorize screenutil extensions or percentage-based spacing in feature code.

## Decide from the right constraints

Use LayoutBuilder for a component's available width: a card in a narrow pane must respond to that pane. Use a narrowly scoped MediaQuery getter or the project's screen-size extension for app-level decisions such as navigation layout. Do not use device width as a substitute for the constraints supplied by the parent. [Flutter adaptive layout](https://docs.flutter.dev/ui/adaptive-responsive/general).

Read the existing breakpoint source before adding comparisons. Keep breakpoints in the shared layout layer; take values from the project's product/design requirements. A new project's thresholds are a design decision, not a new literal in every widget.

## Build from content

- A reference artboard is a capture size, not a fixed viewport requirement. Keep fixed icon/avatar sizes where the design actually calls for them.
- Let text-bearing cards, forms and buttons grow. Use flex, wrapping and shared max-width constraints where appropriate; avoid IntrinsicHeight/Width on large repeated content just to force alignment.
- Make content that can overflow scrollable, while keeping a single clear scroll owner. Do not put every layout in a nested SingleChildScrollView or duplicate the Body's scaffold.
- Account for the keyboard and safe areas through the existing AppScaffold/layout contract. Avoid both double insets and compensating hardcoded top/bottom padding.
- Preserve reading order when switching columns and panes. Use `flutter-accessibility-rtl` for direction, focus and text-scale behavior.

## Check the changed behavior

Check the smallest supported container, the design size and the largest supported target, including large text and keyboard-open forms where relevant. Test constraints rather than only the simulator's default screen width. Existing/design-required goldens may cover targeted variants; create general tests only within the established test policy.

Report the dimensions, state and constraint that were checked. If runtime inspection is unavailable, report that limit; compilation alone does not establish responsive behavior.
