# Optional strict handoff gate

Use this only when the user asks for an auditable theme-stage proof, such as a release review or a disputed handoff. The default handoff is the mapping report, font audit and inspected component comparisons described in the skill. The gate adds a role ledger that binds every observed node to its consumer, runtime probe and visual evidence, and refuses completion when any link is missing. It is slow to prepare; do not build it by default.

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
