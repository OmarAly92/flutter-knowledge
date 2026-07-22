# Playbook — Design-First From HTML

Concrete techniques per phase. Code snippets are proven from real runs; adapt paths/names.

## §0 Assumed project shape (my Flutter template — the DEFAULT)

Unless the repo clearly differs, assume and use these; if the project lacks them, create them
in this shape rather than inventing another:

- **Skin**: `lib/core/app_themes/colors/` — abstract `AppSkin` (core slots + derived getters)
  + `LightSkin`/`DarkSkin`; `SkinCubit` (persisted via `CacheHelper`) → `SkinScope` →
  `context.skin.<getter>`; `AppThemes.fromSkin()` builds `ThemeData`. Never raw `Color(0x…)`
  in feature code.
  If the project's `flutter-knowledge` conventions default to a single flat color-constants class
  but the design ships a real working light/dark toggle (not just a static palette), this skin
  shape wins over that flat default — flag the substitution to the user rather than silently
  picking one.
- **Type**: `lib/core/app_themes/text_style/app_text_style.dart` (`AppTextStyle` +
  `FontWeightHelper`); keep legacy `styleNNWeight` getters working, add the semantic scale.
  Font name constants in `AppStrings`.
- **Motion**: `lib/core/app_themes/app_motion.dart` (`AppMotion`, sealed).
- **Radii/spacing**: `AppConstants` in `lib/core/utils/app_constants.dart` (`radiusXs…radiusPill`).
- **Core widgets**: `lib/core/widgets/` (AppText, AppScaffold, PrimaryButton, SecondaryButton,
  AppTextField, spacing widgets, …) — restyle these, add design primitives beside them.
- **Architecture**: invoke the `/flutter-knowledge` skill (REQUIRED when available) — it is
  the authority; follow it exactly. Summary of its shape — features in
  `lib/feature/<feature>/presentation/<screen>_screen/` (`logic/` cubit+state part files,
  `ui/` + `ui/widgets/`), Cubit-only, screen/body split, BlocProvider in `app_router.dart`,
  DI via `ServiceLocator._<feature>FeatureSetup()`.
- **Strings**: every user-facing string is `LocaleKeys.x.tr()` (easy_localization, en + ar) —
  add keys via the `add-translation` skill when present. RTL must work.
- **Gate**: `flutter analyze` clean after every phase; no new warnings.

Each screen's `<screen>.md` implementation brief must state these conventions explicitly (cleared
sessions in another project may not have the skills auto-loaded).

## §1 Explore the prototype

- Open the HTML in the browser pane; resize to mobile (375×812).
- Native clicks may miss (scaled screenshots) — drive the app with JS instead:
  ```js
  [...document.querySelectorAll('button')].find(b => b.textContent.includes('Continue'))?.click()
  ```
  For React inputs, set value via the native setter then dispatch `input`:
  ```js
  const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
  set.call(inp, 'text'); inp.dispatchEvent(new Event('input', {bubbles: true}));
  ```
- Walk EVERY screen, wizard step, sheet, and both themes (`document.documentElement.setAttribute('data-theme', 'light')`).
- **Verify structure, don't assume**: list interactive elements + their `getBoundingClientRect()`
  to discover the real navigation (a side rail / drawer may hide off-screen at mobile width).
- **Verify gestures live**: use click-drags (horizontal + vertical, both directions) and check
  app state before/after (e.g. which nav item has `is-active`). Check wrap-around.
- Read the prototype's CSS comments — they often state intended behavior verbatim
  (e.g. `/* swipe right to open */`).
- If no live-browser/CSSOM tool is available in this environment, fall back to headless
  `puppeteer-core` + a system Chrome install for interactive verification too, not just phase 6
  screenshots — script the same click/drag driving and read real DOM state (`classList`,
  `getBoundingClientRect`) after each step rather than skipping verification.
- Note broken assets (images/fonts) and report them to the user early.

## §2 Skins / colors

Extract, don't read the file (standalone exports escape CSS into JS strings):
```js
for (const ss of document.styleSheets) for (const r of ss.cssRules)
  if (r.selectorText && /:root|data-theme/.test(r.selectorText)) out[r.selectorText] = r.style.cssText;
```
This yields the light (`:root`) and dark (`[data-theme="dark"]`) token sets.

Then map onto the project's skin layer (Flutter template: abstract `AppSkin` with derived
getters + `LightSkin`/`DarkSkin`; flow SkinCubit → SkinScope → `context.skin`):
- Map semantic tokens (page/surface/sunken/elevated, fg 1-2-3, border default/strong/subtle,
  brand + hover + soft pair, status colors + soft tints) to existing slots.
- **Grep for consumers before deleting** template slots that don't fit the design; remove the
  zero-consumer ones.
- Add design-specific slots as DERIVED getters where possible (e.g. `primaryGlow => primary @25%`,
  `composerBackground => elevated @92%`, `focusRing`, gradients) so both skins inherit them;
  override per-skin only where the design differs (shadows, barriers, elevated fills in dark).
- Convert rgba alphas precisely: `0.07 → 0x12`, `0.12 → 0x1F`, `0.14 → 0x24`, `0.25 → 0x40`.
- Cross-check against COMPONENT rules (§5) — cards may use the *subtle* border, icon tiles the
  *sunken* surface; token tables alone mislead.

## §3 Fonts + text styles

- List `@font-face` via CSSOM (family/weight/style/src) and `document.fonts` (what loaded).
- **Fonts are usually embedded.** Two layouts seen:
  - `src: url("data:font/otf;base64,…")` directly, or
  - `src: url("<uuid>")` + a JSON asset map elsewhere in the file:
    `"<uuid>":{"mime":"font/otf","compressed":true,"data":"<base64>"}` — base64-decode then
    zlib-decompress (try gzip/raw wbits), verify magic bytes (`OTTO`/`\x00\x01\x00\x00`).
- woff2 → Flutter needs ttf/otf: `pip install fonttools brotli`, load `TTFont`, set
  `flavor = None`, save. Variable fonts (`fvar` present): instance static weights with
  `fontTools.varLib.instancer.instantiateVariableFont(f, {'wght': w})`. Unicode-range subsets
  don't merge cleanly — take the latin subset and note the limitation.
- Before instancing anything, check whether declared `@font-face` weights actually point at
  distinct assets — some exports reuse one file (often a variable font's default instance)
  across multiple declared `font-weight` values. Compare `src` targets/UUIDs across weight rules;
  don't assume N declared weights means N real weights.
- **Check embedded fonts for licensing red flags** before recommending they ship: read the font's
  `name` table (`fontTools.ttLib.TTFont(path)['name']` — copyright/manufacturer/designer entries)
  for anything indicating a proprietary third-party brand unrelated to the target app. Flag it to
  the user instead of silently embedding — "found inside the file" does not mean "cleared to
  redistribute."
- Only ask the user to download what genuinely isn't embedded — do not silently fetch a
  replacement yourself (e.g. pulling a same-named family from Google Fonts/GitHub) without saying
  so first. When the missing font is a plain Google Font referenced by name only, prefer pointing
  the user at the `google_fonts` package over manually vendoring instanced static weights —
  simpler, and avoids picking a font version/subset unilaterally.
- Wire: pubspec font families (weights + italics), font-name constants, and the semantic type
  scale from the CSS tokens (`--fs-*`, `--lh-*`, `--tr-*`): height = lh ratio directly;
  letterSpacing = em × fontSize. Keep any legacy numeric getters working; add semantic getters
  (display/heading/body/caption/overline/code/badge/wordmark).
- Check glyph coverage (e.g. Arabic) and keep the project's fallback font in the chain.

## §4 Motion

Extract: `--dur-*` and `--ease-*` tokens, every `@keyframes` body, and unique
`animation:`/`transition:` usages (regex over the CSSOM dump). Produce one sealed constants
class: Durations (fast/base/slow + screen-transition + any longer emphasis + loop durations),
Curves (exact cubic-beziers — keep overshoot values like 1.4), and keyframe deltas
(fade-up offset, slide-up offset, pop scale, bounce/float amplitudes). No ad-hoc
`Duration`/`Curves` anywhere afterward.

## §5 Core widgets

Dump ALL component rules once and save for reference:
```js
for (const r of ss.cssRules) if (r.selectorText?.startsWith('.prefix-')) out.push(r.cssText);
```
Then:
- Restyle existing shared widgets (primary/secondary buttons, text field, dialog, sheet handle,
  dots indicator, press effect) to the exact specs: min-heights, paddings, radii, borders,
  shadows (glows!), text styles, press scales.
- Update the radius/spacing constants class to the design scale (xs…pill).
- Update theme-level defaults (button shape, dialog/sheet shapes, barrier colors).
- A fixed top padding standing in for a status-bar/notch inset in a fixed-viewport mockup (common
  in header/hero components) should become `SafeArea`, not a literally-ported px value — call
  this out explicitly rather than treating every measured number as sacred.
- Create the design's primitives as new core widgets (orb, typing dots, badge, chip, segmented
  control with sliding thumb, check circle, icon button, entrance wrappers fade-up/pop-in).
- Everything consumes skin + text + motion tokens only. Translucent bars pair a skin alpha color
  with a BackdropFilter blur.
- Run the analyzer clean; don't add new warnings.

## §6 Docs + prompts (`docs/design/`)

Structure (see templates.md for file contents):
```
docs/design/
  README.md  colors.md  typography.md  motion.md  components.md
  <screen>/          # one dir per screen incl. the navigation shell
    <screen>.md      # full spec + self-contained implementation brief — ONE file
    *.png            # headless screenshots (dark default; every step/sheet/dialog/state)
```
**One file, one dir per screen — sheets/dialogs merge in.** Never emit a separate `prompt.md`
and never give a bottom sheet or dialog its own dir. A sheet/dialog that a screen opens is
documented as a subsection inside that screen's `<screen>.md` (its screenshots go in the same
dir), so the agent that builds the screen builds its sheets and dialogs in the same pass — split
files/dirs cause two agents to collide or one to miss the piece entirely. Promote a sheet/dialog
to a shared core widget in `components.md` ONLY if it is genuinely opened from many screens.
Screenshots — headless Chrome via puppeteer-core (no browser download):
```js
puppeteer.launch({executablePath: '<system Chrome>', headless: 'new'});
page.setViewport({width: 375, height: 812, deviceScaleFactor: 2});
```
Script the same JS walk from §1 (click by text, fill inputs), `waitUntil: networkidle0`,
**wait ~0.9–1.5s after each navigation** (entrance animations start at opacity 0), shoot every
screen, wizard step, sheet (close sheets by clicking the veil), and special shell states
(drawer open). Verify a couple of PNGs by reading them.

Before writing any screen brief, build the **screen → feature map** in `README.md` from the
project's real feature tree (consult the `flutter-knowledge` skill) — the canonical owning-feature
path for every screen. Each brief copies its own row verbatim and orders the builder to read
`docs/design/README.md` and invoke `flutter-knowledge` before any Dart, so no screen's UI lands in
the wrong feature. Note the launcher-vs-owner trap: a screen opened from another feature's screen
still belongs to its OWN feature.

Write the shared docs from the extracted tokens (tables mapping design token → hex per theme →
skin getter), then each screen's single `<screen>.md` (spec + brief + any owned sheets/dialogs).
Finish by updating the project's
CLAUDE.md: design phase status, "design system complete — reuse, don't recreate" inventory,
and pointers to `docs/design/` + the one-`<screen>.md`-per-screen convention (spec + brief in a
single file; sheets/dialogs merged into their owning screen).
