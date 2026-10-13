---
name: html-to-widget
description: The translation contract from an HTML/CSS design prototype to Flutter widgets — computed styles read in a browser with scripts/layout-tree.js, CSS flex to Row and Column, gap to VerticalSpace/HorizontalSpace, every value through context.tokens, existing core widgets reused, JS-toggled states as cubit states. Use whenever an HTML prototype, mockup file or URL is the design for a screen or component you are asked to build, even when the request is casual ("build this screen from the prototype", "make it match the HTML"). Also use for whole-app HTML design planning and source inspection; use set-theme-from-html to apply complete foundations/assets after shared core exists. For a Figma frame use figma-to-widget instead.
---

# HTML to Widget

## Invocation

`/html-to-widget <html-design-path> [screen or task]`

Read `$ARGUMENTS` as the HTML source path followed by optional screen selection or task instructions. On harnesses that pass invocation text without substituting `$ARGUMENTS`, read the text following the skill name instead.

```text
/html-to-widget ./design/login.html
/html-to-widget "~/designs/My App/prototype.html" build the login screen
```

Treat a quoted path as one argument. Resolve relative paths from the current project directory, expand a leading `~/` to the user's home directory, and verify the file exists and is readable before opening it. Treat the path as data, not shell code. Use this explicit source throughout extraction, implementation and visual verification; do not substitute another HTML file found in the repository. An HTTP(S) design URL can also be supplied in place of the path.

If the argument is omitted, use an unambiguous HTML source already supplied in the current request or conversation; otherwise ask for its path. If the supplied path is missing or unreadable, report that exact path and request a correction. For a single-screen HTML file, proceed with implementation. For a multi-screen prototype, use the requested screen/task or established scope; if neither selects a scope, ask which screen to build before implementing the whole prototype.

For implementation, read the [project configuration contract](../flutter-init/references/configuration.md) before applying package-specific instructions. Keep its conventions and naming; adapt package-specific examples through the selected mechanics.

The failure mode this prevents: eyeballing a screenshot of the prototype, or copying pixel positions, and rebuilding it with `Stack`, fixed sizes and literal colors. The CSS already says how the layout behaves — flex direction, gaps, growth, alignment. Read it and map it.

## Task route

Follow the [task workflow](../flutter-knowledge/references/workflows.md): build a requested single screen immediately, produce briefs for whole-app planning, and continue through every screen for explicit whole-app implementation. Planning uses the [shared design briefs](../flutter-knowledge/references/design-briefs.md) and does not require configuration creation or Flutter tooling. This skill owns source inspection; convention skills own implementation and `visual-verification` owns source comparison.

For whole-design theme/asset preparation after `/flutter-core`, use [set-theme-from-html](../set-theme-from-html/SKILL.md) before building screens. Read its `docs/design/` mappings/import evidence and validate source freshness; prepared tokens/assets do not establish screen fidelity or replace current project API inspection. Single-screen work retains its scoped route.

## Reusable source inputs

Before repeating source extraction, check the [source/profile cache](../visual-verification/references/design-cache.md). Reuse only validated facts/references for the exact screen/state/profile and current dependencies/renderer. HTML hashes alone do not cover external assets; Figma URLs alone do not establish a current revision. Unknown freshness is a miss. Current source facts override stale briefs; report disagreements. Cached facts do not replace live project API/component discovery, token decisions, current Flutter captures or comparisons.

## Prerequisite

Open the prototype in a browser you can drive (a browser tool with JS eval, or headless Chrome) at the design's viewport: 375×812, or the inner size of the device frame the prototype draws. Prototypes are often one file with many screens switched by JS — call its functions or `element.click()` to reach the screen and state you are building. If you only have a screenshot, say so before starting: every value read off pixels is a guess. Ask for the HTML.

For foundation extraction or whole-app planning, read [source-extraction.md](references/source-extraction.md) for computed themes, embedded fonts, motion and component states.

## Read the layout with the script

`scripts/layout-tree.js` walks an element and returns its subtree as compact JSON. Defaults are left out, so every key present is a decision in the design:

- `tag`, `id`, `cls` (the classes), `hidden`; the border box `x`, `y` (relative to the root), `w`, `h`; `text`, the element's own text (80 characters at most); `children` (an `<svg>` has none).
- Layout: `display`; flex `dir`, `wrap`, `justify`, `align`; grid `columns`; `gap`, or `rowGap` and `colGap`; on a child, `grow`, `shrink` (only when `0`), `basis`, `self`.
- Position: `position`, with `top`/`bottom` and `left`/`right` (for absolute or fixed, the nearer of each pair), and `z`; `transform`.
- Box: `padding` and `margin` as `[top, right, bottom, left]`; `border` (`"1px #3a3936"`, or one per side); `radius` (one value or `[top-left, top-right, bottom-right, bottom-left]`, a percentage kept as a string such as `"50%"`); `bg`, `bgImage`, `shadow`, `opacity`, `overflow`.
- Text: `color` and `font` (`family`, `size`, `weight`, `lineHeight`, `letterSpacing`, `align`, `transform`). An input's `type`, `placeholder` and `value` (a password masked); an image's `src`; `before`/`after` pseudo-elements (`content`, `w`, `h`, `bg`, `radius`).
Sizes are px numbers. Colors are `#rrggbb` (`#rrggbbaa` with alpha), inside `shadow` and `bgImage` too.

- Browser tool: evaluate the file's contents in the page, then `JSON.stringify(layoutTree('<selector>'))`.
- Headless Chrome (puppeteer): `await page.addScriptTag({ path: '<skill-dir>/scripts/layout-tree.js' })`, then `await page.evaluate(() => layoutTree('<selector>'))`.
- `layoutTree(selector, { hidden: true })` also returns `display: none` subtrees, flagged `hidden: true` — the states the JS reveals; a hidden box measures 0, so measure hidden elements in the state that shows them.

- `captureComposition(selector, { captureTarget })` returns the same tree plus the capture boundary and visible content outside the screen subtree (drawer handles, app-shell navigation, overlays, generated decoration). Run it on every state you will compare so the Flutter composition includes what the reference PNG shows; see [source-extraction.md](references/source-extraction.md#capture-boundary-and-visible-composition).

Run it on the screen's root, then on each sheet, dialog and state. Do not reimplement it or read styles by hand.

## The mapping

| CSS | Flutter |
|---|---|
| `display: flex; flex-direction: column` | `Column` |
| `flex-direction: row` | `Row` |
| `gap` | `VerticalSpace(tokens.space.x)` / `HorizontalSpace(tokens.space.x)` between children |
| `padding` | `EdgeInsets` with `tokens.space`; the screen's side padding is `tokens.space.screenH` |
| `justify-content` | `mainAxisAlignment` (`space-between` → `spaceBetween`, `flex-end` → `end`) |
| `align-items` | `crossAxisAlignment` (`center`, `stretch`, `flex-start` → `start`) |
| `flex: 1` / `flex-grow` | `Expanded` (`Flexible` when it may also shrink) |
| `width: 100%` inside a column | `CrossAxisAlignment.stretch` |
| `max-width` | `ConstrainedBox(constraints: BoxConstraints(maxWidth: …))` |
| `flex-wrap: wrap` | `Wrap` |
| `display: grid` | `GridView` (`SliverGrid` inside a scroll view) |
| `overflow: auto` / `scroll` | `SingleChildScrollView`; repeated rows → `ListView.builder` |
| `position: absolute` | `Stack` + `Positioned` — only where boxes overlap |
| `position: fixed` / `sticky` bar at the bottom | `AppScaffold(bottomNavigationBar: …)` |
| `border-radius` / `overflow: hidden` | `tokens.radius.<step>` / `ClipRRect` with it |
| `box-shadow` | `tokens.elevation.low` / `.high` |
| `color`, `background` (`var(--…)`) | `tokens.skin.<slot>` |
| `font-*` | `tokens.text.<style>` + `.copyWith(color: …)` |
| `transition`, `@keyframes` | `tokens.motion` |
| `<button>`, `<input>`, `<img>`, `<svg>` | the project's core button, input and image widgets |
| An `<input>`'s `height` / `min-height` | the core text field's vertical content padding, (height − line height) ÷ 2, as a spacing step like any padding. `InputDecoration.constraints` lays out at that height but paints the fill and border only around the text |
| Repeated sibling markup | one item widget + `ListView.builder` |
| Class variants (`.btn--primary`, `.btn--ghost`) | one widget with a parameter |
| A class or `display: none` toggled by JS | a cubit state, rendered with `BlocBuilder` |
| `:disabled` / `:active` / `:hover` | `onPressed: null` / the pressed state / nothing on touch |

## Rules

**Flex first.** Flex and normal flow become `Row` and `Column`. `Stack` only where boxes overlap — a badge on an avatar, a floating button over content. Check `x`/`y`/`w`/`h` before reaching for one.

**Never hardcode the viewport.** 375 is the artboard, not the screen. Fixed sizes only for things fixed on every screen: an icon, an avatar, a dot.

**Every value goes through a token.** Match each color, size, radius, shadow and duration to the tokens in `lib/core/theme/` by value. List what does not match and report it before writing code; `flutter-app-theme`'s "When a value becomes a token" decides whether each one is built with the nearest step or added as a token.

**Reuse before building.** A button, input, chip or sheet in the prototype is almost always a core widget already. Search by role in `lib/core/widgets/<role>/` (`class .*Button`), not by the name you expect.

**Change a core widget only through a parameter.** A core widget's look is every screen's look. When the design needs one to look different here — a height, a padding, a line height — add a parameter whose default keeps today's look, and pass the new value from this screen. When the core widget is broken — an overflow, a crash — fix it, and name the fix in your report.

**Skip the mockup chrome.** A fake status bar, notch, home indicator or device frame is not part of the screen; `AppScaffold` and `SafeArea` handle the real ones.

**Text is never a literal.** Content goes through `LocaleKeys` (missing keys via `add-translation`), style through `tokens.text`.

## Example

```css
.summary { display: flex; flex-direction: column; gap: 12px; padding: 16px 20px;
           background: var(--surface); border-radius: 20px; box-shadow: var(--shadow-low); }
.summary .row { display: flex; align-items: center; }
.summary .label { flex: 1; font: 600 15px/20px var(--font-text); color: var(--text-primary); }
.summary .btn--primary { width: 100%; }
```

```dart
class SummaryCard extends StatelessWidget {
  const SummaryCard({super.key, required this.total, required this.onSave});

  final String total;
  final VoidCallback onSave;

  @override
  Widget build(BuildContext context) {
    final tokens = context.tokens;
    final label = tokens.text.headingSm.copyWith(
      color: tokens.skin.textPrimary,
    );
    return Container(
      padding: EdgeInsets.symmetric(
        vertical: tokens.space.lg,
        horizontal: tokens.space.xl,
      ),
      decoration: BoxDecoration(
        color: tokens.skin.surface,
        borderRadius: tokens.radius.card,
        boxShadow: tokens.elevation.low,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(child: AppText(LocaleKeys.xTotal.tr(), style: label)),
              AppText(total, style: label),
            ],
          ),
          VerticalSpace(tokens.space.md),
          PrimaryButton.expand(text: LocaleKeys.xSave.tr(), onPressed: onSave),
        ],
      ),
    );
  }
}
```

`headingSm` stands for whichever text style is 600 15/20 in the project; each step is the token whose value equals the px value.

Apply the [early design decision](../flutter-app-theme/SKILL.md#early-design-decision) before committing to unmatched mappings.

## Source handoff

1. Open the prototype at its viewport; drive its JS to the screen and state.
2. Run `captureComposition` (and `layoutTree`) on the screen's root against the real capture boundary, and on each sheet, dialog and state; carry visible outside-screen content into the plan.
3. Match every value to a token; report unmatched and off-scale values before writing code.
4. Mark which nodes are existing core widgets and find each one.
5. Return source facts and reusable-component mappings to the selected workflow. Planning records these in briefs; implementation invokes the mapped convention skills and finishes with per-screen visual verification. Do not write Dart during planning.

## Common mistakes

- A `Container` for every `div`. One `Container` holds padding, color, radius and shadow together; a `div` that only groups children is the parent `Column` or `Row`.
- One enormous `build()`. Split where the HTML repeats markup or names a component.
- Copying the computed height of text, or of a box that holds text. Heights come from content; fixed heights clip at larger text scale.
- A new widget per CSS class. Classes that only change color or size are parameters of one widget.
- Turning a child's `margin` into `Padding` on it. Space between siblings is a `VerticalSpace` or `HorizontalSpace` in the parent.
