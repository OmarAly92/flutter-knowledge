# Reusing source facts and references

Reuse immutable source facts and reference captures through `scripts/design_cache.py`. Cache checks are read-only; recording writes only the cache manifest. The helper never changes application code, source designs, images or golden baselines. A hit is reusable input, never verified output. Always capture current Flutter output and run every required source comparison.

## Identity and invalidation

Use one cache per screen/state/profile, for example `docs/design/source-cache/login-dark/`. Record:

- The exact local HTML source, or a current materialized Figma/versioned-source snapshot. A URL alone cannot prove unchanged content; check the current remote revision/assets before reusing a snapshot.
- A complete source dependency manifest. Hash every external CSS/script/font/image and runtime-data snapshot affecting this state, either as local files or current materialized remote responses. Self-contained bundles can use an empty file list when their embedded resources are covered by the source hash. Unknown dependencies or unmaterialized remote resources disable reuse. Do not list application component inventories.
- The actual viewport, DPR, skin, locale, text scale, insets, selector/frame, state, deterministic data identity and capture adapter/browser version/platform. Do not invent an adapter identity when the tool cannot establish it.
- Successful source extraction facts, produced by the source reader. HTML uses the bundled layout-tree script; inspect the requested visible state first. Empty/error/hidden states are not successful extraction.

The helper also fingerprints the bundled extractor. It invalidates on changed/missing inputs, profile or renderer changes, and modified/corrupt artifacts. Source directories are hashed recursively; keep cache/report artifacts outside dependency directories. It does not cache package API assumptions, component inventories, implementation decisions, Flutter output or passed checks. Search live and inspect relevant project APIs when code changes.

`profile.json` example structure (use measured values):

```json
{
  "viewport": {"width": 375, "height": 812},
  "dpr": 2,
  "screen": "Login",
  "state": "loaded",
  "selector": ".sa-screen",
  "skin": "dark",
  "locale": "en",
  "text_scale": 1,
  "safe_area": {"top": 0, "right": 0, "bottom": 0, "left": 0},
  "data": {"fixture": "login-prefilled-v1"},
  "capture_adapter": "actual-tool/browser-version/platform"
}
```

`inputs.json` has `complete: true`, `files: [...]` and `external_resources: []`. File paths resolve relative to that manifest; source and bundled extractor are added automatically. `complete` is an inspected source-reader conclusion, not a default to fill without checking. Do not put raw remote URLs in `files`; materialize and validate their current content/revision. If completeness is uncertain, write `complete: false` and extract/capture without reuse.

## Cold and warm runs

First successful extraction:

```bash
python3 "<visual-verification-directory>/scripts/design_cache.py" record \
  --source <original-source> --profile <profile.json> \
  --inputs-manifest <inputs.json> --facts <layout-or-frame.json> --cache <cache.json>
```

Before subsequent reuse:

```bash
python3 "<visual-verification-directory>/scripts/design_cache.py" check \
  --source <original-source> --profile <profile.json> \
  --inputs-manifest <inputs.json> --cache <cache.json>
```

A `hit` with `facts_reusable: true` lets the agent read the cached state facts instead of dumping/reextracting a large source. A `miss` requires new extraction; do not relabel old facts as current. No check rewrites/deletes the old cache. Exit0 means validated input reuse,1 miss,2 recording/input error. Read the individual facts/reference reuse fields; exit0 is not a design pass.

## Reference provenance

To associate an archived/provided screenshot, add `--reference <png> --reference-status archived`. The helper verifies image integrity/dimensions and keeps its provenance explicitly archived. A later hit never promotes it to fresh; source freshness remains unverified unless independently established under the completion contract.

For a genuinely captured reference, add `--reference-status fresh --capture-metadata <capture.json>`. At capture time, retain `fingerprint` from the current source/profile inventory, `tool` exactly matching the profile adapter, a timezone-qualified `captured_at` timestamp, and `reference_sha256` computed from the actual captured PNG. The metadata binds that exact image; do not associate it with another same-size file. Capture metadata must describe the actual operation; never generate it afterward to legitimize an old screenshot. The PNG must match viewport×DPR without resizing. Changed provenance/input hashes disable reuse. This is an association/integrity check, not proof that the captured UI state is correct: inspect state, fonts, source identity and contents before approving it.

A reusable reference can remain valid across unchanged tasks; recapture when any identity input changes or freshness cannot be established. Current Flutter output and comparisons are never reused as a pass, and references for other skins/states/locales are not interchangeable.
