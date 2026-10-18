---
name: figma-to-widget
description: Use to build, plan or update Flutter screens/components from Figma frames, including existing-screen UI refreshes that preserve logic. Also covers whole-app Figma planning/foundation extraction.
---

# Figma to Widget

For implementation, read the [project configuration contract](../flutter-init/references/configuration.md) before applying package-specific instructions. Keep its conventions and naming; adapt package-specific examples through the selected mechanics.

The failure mode this prevents: reading pixel positions off the frame and rebuilding them with `Stack` and `Positioned`. That output matches the artboard exactly and breaks on every other screen size. Figma's Auto Layout maps cleanly onto Flutter's layout — use the mapping, not the coordinates.

## Task route

Follow the [task workflow](../flutter-knowledge/references/workflows.md): resolve source/scope, apply its core readiness gate for implementation, build a requested single screen without unnecessary planning, and continue through every screen for explicit whole-app implementation. Whole-app planning uses the [shared design briefs](../flutter-knowledge/references/design-briefs.md) and does not create configuration/core or require Flutter tooling. This skill owns source inspection; convention skills own implementation and `visual-verification` owns source comparison.

Existing-screen updates follow [natural-language design updates](../flutter-knowledge/references/workflows.md#natural-language-design-updates). Resolve the associated frame and current revision, preserve the working logic and update the existing UI. Users do not need to name skills or repeat an unambiguous frame identity.

## Reusable source inputs

Before repeating source extraction, check the [source/profile cache](../visual-verification/references/design-cache.md). Reuse only validated facts/references for the exact screen/state/profile and current dependencies/renderer. HTML hashes alone do not cover external assets; Figma URLs alone do not establish a current revision. Unknown freshness is a miss. Current source facts override stale briefs; report disagreements. Cached facts do not replace live project API/component discovery, token decisions, current Flutter captures or comparisons.

## Prerequisite

Check whether a connected Figma tool is available. If it is, pull the frame and read real values: Auto Layout settings, variables, styles, component instances. If it is not, say so before starting — without direct Figma access every value is read off a rasterized image and is a guess. Ask for Dev Mode access, an inspect export, or the file's variables rather than guessing silently.

## The mapping

| Figma | Flutter |
|---|---|
| Auto Layout, vertical | `Column` |
| Auto Layout, horizontal | `Row` |
| Auto Layout gap | `VerticalSpace(tokens.space.x)` / `HorizontalSpace(tokens.space.x)` between children |
| Auto Layout padding | `EdgeInsets` with `tokens.space`; the screen's side padding is `tokens.space.screenH` |
| Space between | `MainAxisAlignment.spaceBetween` |
| Hug contents | `MainAxisSize.min` |
| Fill container | `Expanded` on the main axis, `CrossAxisAlignment.stretch` on the cross axis |
| Fixed width/height | `SizedBox`, only when the design is fixed on every screen |
| Wrap | `Wrap` |
| Absolute position | `Stack` + `Positioned` — last resort only |
| Frame with clip content | `ClipRRect` with `tokens.radius.<step>` |
| Color variable or color style | `tokens.skin.<slot>` |
| Text style | `tokens.text.<style>` + `.copyWith(color: …)` |
| Corner radius | `tokens.radius.<step>` |
| Drop shadow effect | `tokens.elevation.low` / `.high` |
| Text field frame height | the core text field's vertical content padding, (height − line height) ÷ 2, as a spacing step like any padding. `InputDecoration.constraints` lays out at that height but paints the fill and border only around the text |
| Component instance | an existing core widget from `lib/core/widgets/<role>/` |
| Component variant | a parameter or enum on that widget, not a new widget |
| Prototype interaction that swaps a variant | a cubit state, rendered with `BlocBuilder` |

## Rules

**Auto Layout first.** If a frame uses Auto Layout, the output uses `Row` or `Column`. Reach for `Stack` only when layers genuinely overlap — an avatar badge, a floating button over content. Overlap is the only valid reason.

**Never hardcode the artboard width.** A 375pt frame is a reference, not a target. Fixed sizes appear only where the design is fixed regardless of screen: an icon, an avatar, a fixed-size chip.

**Every value goes through a token.** Match each variable, style and raw value to the tokens in `lib/core/theme/` by value; the Figma name is only a hint. List what does not match and report it before writing code; `flutter-app-theme`'s "When a value becomes a token" decides whether each one is built with the nearest step or added as a token.

**Check for an existing component before building one.** A component instance almost always corresponds to a core widget. Search by role (`class .*Button` in `lib/core/widgets/buttons/`), not by the component's Figma name.

**Change a core widget only through a parameter.** A core widget's look is every screen's look. When the design needs one to look different here — a height, a padding, a line height — add a parameter whose default keeps today's look, and pass the new value from this screen. When the core widget is broken — an overflow, a crash — fix it, and name the fix in your report.

**Variants are parameters.** A component with Default, Pressed, Disabled and Loading variants becomes one widget with parameters — `PrimaryButton(isLoading: …, onPressed: null)` — not four widgets.

**Text is never a literal.** Content goes through `LocaleKeys` (missing keys via `add-translation`), style through `tokens.text`.

Apply the [early design decision](../flutter-app-theme/SKILL.md#early-design-decision) before committing to unmatched mappings.

## Source handoff

1. Pull the frame and read its layer tree against the full exported capture boundary. Include visible ancestor/sibling app-shell layers and overlays; a selected component subtree alone may omit pixels present in the reference.
2. List every distinct value in it. Match each against the tokens; report anything unmatched before writing code.
3. Mark which layers are component instances and find the core widget for each.
4. Return the frame identities, source measurements and component mappings to the selected workflow. Planning records briefs; implementation invokes the mapped convention skills, then visual verification with the matching frame export/profile. Do not write Dart during planning.

## Common mistakes

- Nesting `Container` inside `Container` because the design has nested frames. Collapse them; one `Container` holds padding, color, radius and shadow together.
- One enormous `build()` for the whole screen. Split at the component boundaries the design file already draws.
- `SizedBox(height: 12)` between elements. The design expresses it as an Auto Layout gap; express it as `VerticalSpace(tokens.space.x)`.
- Copying a text layer's fixed height. Heights come from content; fixed heights clip at larger text scale.
