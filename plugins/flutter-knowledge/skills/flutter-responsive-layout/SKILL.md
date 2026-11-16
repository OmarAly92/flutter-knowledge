---
name: flutter-responsive-layout
description: Use for Flutter constraints, breakpoints, overflow and layout exceptions, keyboard/safe-area insets, small screens, large text, tablets or split panes, including layouts from one design artboard.
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

## Fix a layout error

Constraints go down, sizes go up. Read the first layout exception in the log, or `get_runtime_errors` when the [Dart MCP server](../flutter-knowledge/references/dart-mcp.md) is connected; "RenderBox was not laid out" and the errors after it are consequences, not the cause. Find the widget it names in the source, or with `widget_inspector` when the tree is built dynamically.

| Error | Cause | Fix that keeps the conventions |
| --- | --- | --- |
| Vertical (or horizontal) viewport was given unbounded height (width) | A `ListView`/`GridView`/`CustomScrollView` inside a `Column` (`Row`) or another scroll view | Give it the remaining space with `Expanded`, or merge it into the single scroll owner as slivers. A fixed height only when the design fixes one, from `tokens.space`/the design; `shrinkWrap: true` only for a short, bounded list. |
| An InputDecorator … cannot have an unbounded width | A text field (`AppTextField`) directly in a `Row` | Wrap the field in `Expanded` or `Flexible`. |
| A RenderFlex overflowed by N pixels | Children of a `Row`/`Column` need more than the parent gives | Let the text-bearing child flex (`Expanded`/`Flexible` around `AppText`, using the wrapper's max-lines/overflow parameters where it has them), wrap instead of row when content can grow, or make the Body scrollable. Never fix it with a smaller literal size or by clipping. |
| Incorrect use of ParentDataWidget | `Expanded`/`Flexible` not directly inside a `Row`/`Column`/`Flex`, or `Positioned` not directly inside a `Stack` | Move it to be the direct child, or remove the wrapper between them. |

Reload (`hot_reload` when connected), confirm the error is gone and the stripes or red screen are gone, then check the smallest supported width and large text as below. The fix stays in the widget that owns the layout; do not add a scaffold or scroll view to a Body that already has one.

## Check the changed behavior

Check the smallest supported container, the design size and the largest supported target, including large text and keyboard-open forms where relevant. Test constraints rather than only the simulator's default screen width. Existing/design-required goldens may cover targeted variants; create general tests only within the established test policy.

Report the dimensions, state and constraint that were checked. If runtime inspection is unavailable, report that limit; compilation alone does not establish responsive behavior.
