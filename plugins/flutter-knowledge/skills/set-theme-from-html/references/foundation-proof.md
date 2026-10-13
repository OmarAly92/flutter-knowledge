# Foundation application proof

Use this reference during `/set-theme-from-html`, after the owning [source extraction](../../html-to-widget/references/source-extraction.md). It owns the font-selection and role-application audits; it does not replace the theme APIs or the [visual runner](../../visual-verification/references/runner.md).

## Exact semantic roles and consumers

Before theme edits, assign every rendered snapshot node and generated pseudo-element a source role or an explicit exclusion with a reason. A structural container can be excluded when its measured properties have no foundation responsibility; painted decorations, text runs and shared controls cannot disappear into that exclusion. Review outside-screen composition candidates as well. Repeated signatures can share an API, but retain every profile/selector occurrence. Review the whole supplied screen/theme/state inventory; an audit cannot discover states the browser never visited.

Inventory source typography by family, weight, style, size, line-height, tracking and feature/variation settings, including rich spans. Keep exact fractional sizes and text-height ratios. Inventory maximum widths, control heights, padding, gaps, divider geometry and effective task/legal/quiet roles where observed, using source role names rather than a fixed application catalog. A nearby scale step is not an exact match. Record unmatched or conflicting observed roles before screen handoff; resolve them through semantic tokens or scoped variants, or leave them explicitly NOT VERIFIED.

An application row names the actual token/API and consuming core wrapper. Probe values through the project's current `AppTheme`, `AppTokens` or its established older equivalents at the source viewport, scale and skin, after resolving widget states. A Dart literal search alone cannot establish effective defaults. Runtime evidence must come from a test/export that instantiates the actual theme and wrapper, records the resolved style/constraints/paint values and asserts profile/state. Retain and hash that capture code with the theme/consumer files. Inspect its assertions; a handwritten JSON file is not a runtime probe.

For source controls, check each supplied text-only, icon-bearing, loading, disabled, focus, hovered, pressed and selected variant. Measure border box, label line-height, icon box, content box, each padding side, gaps, minimum size, tap target, elevation/shadow and Material state overlays. Material minimum sizes, icon constructors, disabled elevation and overlay defaults can change the result even when the label tokens match. Preserve source paint geometry while retaining the project's accessible tap region; record both separately. When a source control is cropped from a page, Chrome snaps its box to the nearest whole pixel vertically while glyphs keep subpixel horizontal positions, so place the Flutter consumer at the rounded vertical offset and the unrounded horizontal one. Configure defaults and scoped variants through `AppTheme` and the existing core wrapper, preserving its nullable overrides and selected adapters. Do not build a raw themed replica for evidence. Theme owns those defaults/variant APIs; `html-to-widget` owns feature positioning and selecting the appropriate variant.

## Paint and composition

A gradient color slot or shadow token does not implement a source decoration. Every observed glow, orb, ambient field, rim/inset shadow and other paint role needs its actual shared-core consumer and source-backed proof. Record gradient type, colors/stops, coordinate units, center, extent/shape, clipping, opacity, blend mode, bounds and origin, shadows (including inset/rim), transform/origin and animation frame/keyframes. CSS radial extents such as farthest-corner are not Flutter's default radial radius. Record each supplied mode's values instead of reusing a translucent palette by assumption.

Preserve stacking contexts and compositing relative to body, controls and headers. A foreground translucent layer can alter apparent control colors; moving it below the body changes the source. Use a scoped composition/variant API in the existing scaffold or shared widget where needed, while preserving architecture, public defaults and adapters. Do not modify original SVG paths/bytes to fake an overlay or move business layouts into core. Mark unsupported filters, blend modes, inset effects, animation/shaping or installed API capabilities as gaps with the affected roles; do not claim implementation from tokens alone.

## Font plan audit

Run `scripts/audit_fonts.py` before dependent typography implementation and again at theme handoff. It reads original importer metadata/hashes, source snapshot declarations/usages, actual pubspec registrations and a narrowly supported AppFonts constant/consumer binding. It never rewrites files, converts/instances a face, guesses a weight from its basename or substitutes an asset. Install requirements only within existing authorization; `scripts/requirements.txt` includes fontTools and PyYAML.

```bash
python3 "<skill-directory>/scripts/audit_fonts.py" \
  --plan <font-plan.json> --imports <import-report.json> \
  --project <flutter-project> --report <font-audit.json>
```

Font plan v1 fields:

- `schema_version: 1`, `faces` and `uses` lists.
- Each face: unique `id`, importer `asset_id`, `css: {family, weight, style, unicode_range}` and `declaration: {path, sha256, rule}`. `rule` indexes the bound foundation snapshot's structured `rules[].face`; preserve CSS aliases independently of internal font names. The audit also binds the imported resource-reference hash to the selected original URL in this CSS rule (`source_url_index`, default 0, chooses among declared URL sources). CSS `weight` is a string such as `"400"` or `"100 900"`, never inferred from metadata. `unicode_range` is the original declaration, including subsets; omitted CSS descriptors use their declared defaults (`normal` weight/style and `U+0-10FFFF` coverage).
- Each use: unique `id`, complete `profile`, `locale`, visible `text` (concatenated snapshot `textRuns`, including ordinary control values and selected labels), observed ordered `source_families`, numeric `weight`, `style`, requested `axes` by tag, actual Flutter `alias`, ordered `fallback_aliases`, and ordered `selection: [{alias, face_id}]`. `source: {path, sha256, selector}` binds the observed node/profile. For generated literal text or a visible placeholder, `source` adds `pseudo` (including `"::placeholder"`); bind its effective style instead of the host style. Cover every visible run and supplied locale, including nested spans. `unresolvedText` and `textVisibilityUncertain` are gaps: masked/native formatted glyphs, partial clips and internal scrolling cannot receive cmap certification from a guessed string. This helper has no rendered-glyph override; inspect original native rendering and retain NOT VERIFIED until a supported audit adaptation exists. Never export a raw password or assume the platform mask glyph. Compound/escaped CSS generated text also needs supported decoding; do not union unrelated imported faces to claim effective coverage.
- `app_fonts: {path, sha256, symbol}` binds an inspected literal constant assignment such as `static const body = 'BodyAlias';`. `consumer: {path, sha256, expression}` names its actual use, such as `AppFonts.body`. Those files and imported fonts must resolve inside the project. Source snapshots can be retained in the project's design evidence directory for this font audit; sanitize their source identity before shipping. When fallbacks are selected, add ordered `fallback_bindings: [{alias, symbol, expression}]`; every binding must resolve in that same AppFonts file and match the actual consumer’s literal `fontFamilyFallback: [AppFonts.<symbol>, ...]` list. Complex AppFonts expressions require an audit adaptation backed by a runtime export; the current helper cannot certify them.
- If multiple equally registered subsets share an alias/style/weight, each selected record needs `selection_evidence: {path, sha256}` from actual runtime face selection. The bound JSON must contain `selections` with the exact `use_id`, `alias`, original `path`/`sha256`, requested `weight`/`style` and full `profile`. This is an attestation that must be inspected, not permission to guess which subset won. Prefer an original full-coverage source face only when it is actually supplied and the source usage supports selecting it. Never relabel each subset as a different weight.

Only selected aliases/fallbacks contribute coverage, intersected with each selected face's CSS unicode-range. CSS variable weight ranges and requested axes must lie within original `fvar` bounds; a pin at another weight fails. Static requested weights must agree with the source CSS descriptor and actual registration. CSS/pubspec descriptors can legitimately override internal weight/style metadata; retain the original metadata in the report rather than relabeling bytes or certifying shape from it. Usage outside a source descriptor’s declared weight/style (including synthesized styles) remains an explicit unsupported gap; this helper has no synthesis-equivalence override. Duplicate aliases or ambiguous subset selection must be resolved from actual runtime evidence. A PASS means direct cmap/subset coverage for declared usages, not shaping, engine face selection, platform fallback, Arabic appearance or visual approval. Native/generic fallback without original font bytes is a missing capability in this helper; record platform identity and rendered evidence separately and retain NOT VERIFIED for source typography it cannot establish. The command exits 0 for covered declared usages, 1 for audit gaps, 2 for invalid input/dependencies.

## Role ledger and immutable theme-stage gate

Prepare a compact ledger under existing `docs/design/` (task-local raw identities may stay outside the app). Keep states `extracted → applied → visually checked` distinct. Store the original source identity, snapshot/profile, property/value, token/API, actual consumer, runtime probe and visual evidence. `provisional`, `unsupported`, `unchanged` and `unverified` rows need reasons and cannot approve an observed source role. Unprovided roles remain outside the claimed scope; do not manufacture source mappings for them.

Run the gate **before feature work** and retain a new immutable attempt directory with the stage ledger, audit result and a before/after theme delta (changed file hashes/diff, commands and original asset identities). A later screen-stage repair is a new stage and cannot retrospectively approve the earlier delta. The output-directory refusal prevents accidental replacement; retaining the before/after diff is the caller's responsibility.

```bash
python3 "<skill-directory>/scripts/audit_handoff.py" \
  --ledger <theme-ledger.json> --project <flutter-project> \
  --out <new-theme-stage-proof-directory>
```

Ledger v1:

```json
{
  "schema_version": 1,
  "stage": "theme-before-feature",
  "source": {"path": "source/design.html", "sha256": "<actual digest>"},
  "snapshots": [{"id": "profile-a", "path": "source/foundations.json", "sha256": "<actual digest>"}],
  "fonts": {
    "plan": {"path": "font-plan.json", "sha256": "<actual digest>"},
    "imports": {"path": "imports.json", "sha256": "<actual digest>"}
  },
  "visual": {
    "results": {"path": "attempt/results.json", "sha256": "<actual digest>"},
    "inspection": {"path": "inspection.json", "sha256": "<actual digest>"}
  },
  "roles": [{
    "id": "legal",
    "snapshot": "profile-a",
    "selector": "#legal",
    "profile": "<replace with the complete capture profile object>",
    "properties": {
      "font-family": {"source": "SourceFace, sans-serif", "api": "tokens.text.legal.fontFamily", "expected": "ActualAlias"},
      "font-weight": {"source": "400", "api": "tokens.text.legal.fontWeight", "expected": 400},
      "font-style": {"source": "normal", "api": "tokens.text.legal.fontStyle", "expected": "normal"},
      "font-size": {"source": "12.25px", "api": "tokens.text.legal.fontSize", "expected": 12.25}
    },
    "application": {
      "files": [{"path": "lib/core/theme/typography/app_typography.dart", "sha256": "<actual digest>"},
                {"path": "lib/core/widgets/app_text.dart", "sha256": "<actual digest>"}],
      "consumer": {"file": "lib/core/widgets/app_text.dart", "symbol": "AppText"},
      "runtime": {"path": "runtime-values.json", "sha256": "<actual digest>"}
    },
    "visual_rows": ["legal-profile-a"]
  }],
  "exclusions": []
}
```

The JSON illustrates the schema, not a ready-made source mapping: replace placeholders, selectors, APIs and profiles with inspected facts. Evidence paths resolve relative to the ledger; application file paths resolve relative to the project. A role may add `pseudo: "::before"` or `"::after"`. Exclusions contain `snapshot`, `selector`, optional `pseudo`, and `reason`. Every observed node/pseudo must be addressed; this catches omitted decoration/text/control occurrences, but cannot decide whether a stated exclusion is semantically justified. Review the inventory and property completeness explicitly.

`properties` retain exact observed CSS and the intended Flutter representation. For direct visible text (including literal pseudo text), the gate requires every captured color, family, size, weight, style, stretch, line-height, tracking, feature/variation/optical-size and text-transform field. For a non-`none` background image or shadow, it also requires captured size, radius, opacity, background geometry/color, clipping, filter, transform/origin, blend and stacking fields. A row naming only a gradient or font size cannot approve that role. This source-led minimum does not infer missing measurements or establish complete semantic mapping; inspect additional geometry, motion, overlays and state facts. Single-pixel lengths, numeric weights/opacity and line-height are checked for rounding. For Flutter `TextStyle.height`, set `conversion: "line-height-ratio"` and `expected` to measured CSS line-height divided by measured font-size. CSS `line-height: normal` has no ratio: leave `height` null, because `1.0` moves single-line labels in fixed-height controls by about a pixel. Other representations (colors, gradients, shadow lists, constraints, shapes) must record explicit structured `expected` values from the actual API and are checked against the runtime export and PNGs; the helper does not provide a universal CSS-to-Dart converter.

Runtime export v1 is `{"roles": [{"id", "profile", "consumer", "properties": {"<CSS property>": {"api", "value"}}}]}`: replace the abbreviated fields with their actual values. Consumer and full profile must exactly match the ledger. The narrow declaration check requires a class under `lib/core/` extending `StatelessWidget`, `StatefulWidget` or `CustomPainter`; token-only declarations cannot be consumers. Projects using another wrapper base need an explicitly supported audit adaptation and remain NOT VERIFIED until then. Bind all changed token/theme/wrapper and probe-camera files in `application.files`, not just the file that declares the token. Bind each profile’s foundation snapshot as the source cache `facts` file used by its owning visual row; the gate requires its hash to match `cache_facts`. Source-backed visual camera rows must render that consumer through the applied theme and cover the named properties at the recorded profile. Link the measured primitives; a composite row must also list every required child in `visual_rows`. Every child must pass; missing, failing or unavailable children block completion.

The gate re-runs the font audit, accounts for every visible text occurrence (DOM runs, control values, selected labels and placeholder styles) and unresolved/partially visible glyph gap in the supplied snapshots, verifies all bound files/hashes, compares snapshot values, requires runtime property/consumer/profile evidence, validates the owning visual runner's original results and inspection, rechecks cache/source freshness and re-runs its comparator at unchanged default settings. It checks current PNG dimensions/profile files and original source identity. It does not trust a ledger status, reviewed-status string, imported assets, capture exit or style numbers as visual verification. Default comparator settings/scoring/exits remain owned by the runner. An attested PNG inspection and runtime export still require human/agent inspection of their content and capture code; hashes prevent drift, not fabricated attestations. A cache hit validates source reuse only.

It writes `ledger.json` and `audit.json` to a previously absent output directory. Exit 0 means all declared roles reached visually checked with covered font usages and no unassigned observed nodes; 1 retains a NOT VERIFIED proof with gaps, 2 reports invalid arguments/evidence or an existing output directory. Do not relabel a partial proof as complete. Hand the source inventory, exact role APIs/variants, imports, frozen stage delta, audit and remaining gaps to `html-to-widget`; feature work retains its own verification gate.
