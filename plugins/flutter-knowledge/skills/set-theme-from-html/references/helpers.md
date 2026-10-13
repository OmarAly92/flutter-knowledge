# Supporting helpers

## Browser snapshot

Load the shared `html-to-widget/scripts/layout-tree.js`, then `set-theme-from-html/scripts/foundation-snapshot.js` in the actual design browser. After reaching and settling each observed state:

```javascript
await document.fonts.ready;
captureFoundations({ selector: '#current-view', profile: { skin: 'light', state: 'loaded' } });
```

Use selectors/profile values from the source, not these example identities. The return includes shared layout/composition geometry, exact computed typography/layout/paint properties, text runs with locale/rects, border/content geometry and structured CSS font-face descriptors and custom properties on visible candidates, accessible CSSOM rules with stylesheet bases, font/keyframe declarations, declared document font load status, resource references and inline SVG provenance. `nodes` uses the owning composition capture's ancestor visibility, viewport/overflow clipping and sampled control exposure; each node retains its `visibility` bounds. Optional `captureTarget` forwards the actual source capture boundary to that owner; otherwise it uses the viewport. Fully hidden, clipped or outside-boundary candidates do not become visible font usages. Partial clipping, internal control scrolling and complex clipping retain `textVisibilityUncertain`; geometry/hit tests are not pixel glyph proof.

Ordinary text/email/url/tel/search input values, textarea values, explicit button labels and closed single-select option labels populate `textRuns`; visible placeholders use `pseudo["::placeholder"]` with their own computed style. Native formatted/listbox text and masks retain `unresolvedText`/unknown glyph facts. Password or CSS-masked values are never exported or replaced by an assumed bullet glyph. The returned layout trees omit input/textarea value/text fields; use the scoped node text evidence instead. Placeholder text is captured only while `:placeholder-shown`; supplied values, placeholder variants, locales and native states still need rendered inspection. CSSOM access failures, missing SVG references, iframes and shadow roots remain gaps. The snapshot does not navigate, calculate dependency hashes, import resources, guarantee glyph fallback, infer roles or grant verification. Raw source URLs may contain machine paths or queries: sanitize reports and keep raw snapshots only in task-local evidence.

## Asset import

Use Python 3.10+, Pillow for actual raster integrity checks and fontTools for font format/metadata/glyph checks (helper dependencies are listed in `scripts/requirements.txt`). Use installed dependencies; report missing capabilities rather than calling format signatures verified. Create an explicit JSON manifest from inspected browser/source facts, with one record per resource:

```json
{
  "assets": [
    {"id": "hero", "kind": "images", "name": "hero", "url": "../img/hero.png", "base": "file:///supplied/design/css/app.css"},
    {"id": "brandIcon", "kind": "icons", "name": "brand_icon", "url": "data:image/svg+xml;base64,..."},
    {"id": "bodyFace", "kind": "fonts", "name": "body_regular", "url": "fonts/body.ttf", "base": "file:///supplied/design/index.html", "text": "Supplied glyphs"}
  ]
}
```

The abbreviated data URI illustrates the schema; replace it with actual source bytes. `base` is the actual document/CSS URL, not a guessed directory; it is required for relative URLs. `id` is unique and stable, `name` is a safe readable basename, `kind` is `images`, `icons` or `fonts`. `text`, when supplied for a font, checks direct cmap coverage for those codepoints (including spaces, excluding Unicode control and formatting characters). This does not prove shaping, fallback selection or rendered glyph coverage; verify those in the browser and Flutter output. Preserve original license/provenance records outside this manifest, associated by id/hash. Fonts' actual name/weight/style/axes and glyph count appear in the report; use them with declared CSS face usage rather than treating metadata as the whole typography decision.

```bash
python3 "<set-theme-from-html-directory>/scripts/import_assets.py" \
  --manifest <source-derived-manifest.json> --project <flutter-project> \
  --report <task-local-import-report.json>
```

The helper fetches only explicit manifest URLs, with 15-second request timeout, 16 MiB per resource and 128 MiB per invocation. HTTP(S) GETs reject URL credentials, carry no cookies/custom credentials and permit at most three redirects, rejecting unsupported schemes/credential-bearing redirects. Remote failures report only safe resource ids. Local paths and data URIs also observe byte limits. File URLs support local hosts only; query/fragment do not become filenames. Fonts, SVG and PNG/JPEG/GIF/WebP/BMP/TIFF/ICO are integrity-checked; unsupported formats remain errors. SVG references must resolve within its standalone document; currentColor is preserved and reported for explicit inheritance/render checking.

Verified bytes are copied with exclusive creation under assets directories, never through a project-relative symlink escape. Existing same-kind bytes are reused, collisions use a content-hash suffix, and unrelated files are never overwritten. Failed resources do not stop independent imports; report rows retain errors and the command exits 1 if any occurred, 0 if all imports succeeded, 2 for invalid manifest/project/report arguments. A report outside the project avoids shipping original source-machine identity; it contains safe ids, portable destination paths, hashes, resource-reference hashes, actual format/metadata and created/reused/error status. It never rewrites AppAssets/pubspec, converts fonts, strips SVG, or sets a theme/visual verified flag. Import success does not establish that Flutter's selected decoder can render the format: verify installed APIs and actual output.

## Application audits

Read [foundation-proof.md](foundation-proof.md) for the font-plan contract and command. `audit_fonts.py` checks actual selected original registrations and direct coverage. The optional `audit_handoff.py` ([strict handoff gate](strict-handoff-gate.md)) binds extracted roles to runtime consumers and revalidates the owning visual runner evidence at its default settings, writing a new immutable theme-stage proof. Neither helper infers semantic roles, engine font selection, unvisited states or performs PNG inspection.
