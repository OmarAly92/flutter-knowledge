# Verification runner

`scripts/run_verification.py` runs the project's existing Flutter golden camera once in batch mode, compares each declared row with `compare.py --json` at its default settings and writes a new attempt directory. Configure the camera to write only the declared candidate paths; `--update-goldens` delegates writes to that test. A numeric PASS is reported as NOT VERIFIED until a recorded inspection accepts it.

```bash
python3 "<skill-directory>/scripts/run_verification.py" run --manifest <manifest.json> --out <evidence-dir> [--project <flutter-project>]
python3 "<skill-directory>/scripts/run_verification.py" inspection-template --results <attempt>/results.json > inspection.json
python3 "<skill-directory>/scripts/run_verification.py" finalize --results <attempt>/results.json --inspection inspection.json --out <reviewed-dir>
```

`run` exits 0 when every compared row passes numerically (rows with no reference are NOT_RUN), 1 when any row differs, 2 for capture, dimension, comparator or input errors. Invalid manifests, profiles or commands raise before any process starts. A command that cannot launch has `exit_code: null`, retained stderr and ERROR rows; it has no fabricated process exit.

## Manifest v1

```json
{
  "schema_version": 1,
  "project": "../project",
  "capture": {"command": ["flutter", "test", "test/golden_capture_test.dart", "--dart-define=CAPTURE_ROUND={attempt}"]},
  "rows": [
    {
      "id": "login-dark",
      "label": "Login / dark",
      "kind": "source",
      "profile": "profiles/login-dark.json",
      "source": {"path": "design/prototype.html", "inputs_manifest": "cache/inputs.json", "cache": "cache/login-dark.json"},
      "reference": {"path": "reference/login-dark.png"},
      "actual": "test/goldens/{attempt}/login-dark.png"
    },
    {"id": "login-dark-ar-2x", "label": "Login / dark / Arabic 2x", "kind": "regression",
     "profile": "profiles/login-dark-ar-2x.json", "actual": "test/goldens/{attempt}/login-dark-ar-2x.png"}
  ]
}
```

- Paths in rows resolve relative to the manifest; `project` is relative to the manifest too, and `--project` overrides it. `actual` is relative to the Flutter project and must contain `{attempt}` and stay inside it.
- Row ids are stable, unique, lowercase `[a-z0-9._-]` slugs. Labels are plain text without `|`; they become the first column of the report and the `--design-screen` values for `flutter-review`.
- `kind: source` requires `source.path` and a reference PNG. `kind: regression` has no source; with a reference it is a baseline comparison, without one it is NOT_RUN. Regression rows never become source design verification and their report percentage cells remain `n/a`; baseline measurements remain in `results.json`.
- `profile` is a `design_cache` capture profile plus `conditions`. `fonts`, `motion`, `pointer` and `expected_state` must be nonblank descriptions; `shadows` must be a boolean; optional `keyboard_inset` must be finite and nonnegative. The Flutter capture must be a readable PNG with exactly the size `viewport × dpr`; a wrong format or size is an ERROR, never resized. The camera must apply and assert every row's profile and expected state; the runner validates declarations and pixel dimensions, not the widget's runtime configuration.
- Batch capture (`capture.command` at manifest level) starts one Flutter process for all rows; the test reads `String.fromEnvironment('CAPTURE_ROUND')` to write `test/goldens/<round>/<row>.png`. The runner adds `--no-pub` and `--update-goldens` (the camera is not an approval) and replaces `{attempt}`. Candidate paths must resolve to distinct files. Per-row mode (`capture.command` inside a row, with `{actual}` and `{profile}`) exists for single-state tools; avoid it for the whole suite, a Flutter process per row is slow. A manifest must use one mode throughout and cannot also declare row commands when it has a batch command.
- Source rows may bind freshness with `source.inputs_manifest` and `source.cache` from [design-cache.md](design-cache.md). Only a fresh capture-time reference bound to the current source can become VERIFIED; no cache, an archived reference or a miss stays NOT VERIFIED.

## Evidence

Each run creates a new attempt directory containing `results.json`, `verification.md`, shared or per-row capture logs and per-row comparator logs (complete stdout/stderr), a copy of each candidate PNG, `diff.png` and `compare.json` when comparison runs. Reruns never overwrite an earlier attempt, and a candidate path that already exists is refused. A failing batch camera marks every row ERROR; a failed per-row camera marks that row ERROR. Partial PNGs are copied and hashed as `uncompared_actual` evidence, never compared. No output from another attempt supplies a missing capture.

`results.json` stores argv, exit codes, profile, the comparator payload (settings, percentages, bounds), cache provenance and SHA-256 identities of inputs and artifacts. Source/reference/profile identities are taken before camera execution; changing them during capture produces ERROR. A reusable source cache also binds its input inventory, dependency files, extractor, extraction facts and capture metadata. The inventory is rechecked to detect newly added directory assets. Candidate, actual, diff, comparator JSON and complete logs are hashed as they are produced.

`verification.md` follows the seven-column evidence table from the skill, with source-backed percentages from `compare.py` and no number for errors, NOT_RUN or regression-only rows. Default settings and comparator exits are passed through without overrides.

## Inspection and finalization

Open the Flutter, reference and diff PNGs at full resolution, check the state, fonts, direction and anything red, then fill the template from `inspection-template`: `inspector`, `inspected_at`, per row `inspected: true`, `outcome` (`accepted` or `rejected`) and notes naming what was read. The template carries the current artifact hashes. `finalize` refuses the inspection if the results, source, reference, profile, candidate, diff, logs or bound source cache artifacts changed since the run or the inspection, if the source dependency inventory changed, if any row is missing or uninspected, or if the output directory exists. It writes `reviewed_results.json` and a reviewed `verification.md` in a new directory and leaves the original results untouched. Writing `inspected: true` records an attestation; the tool cannot perform the PNG inspection for you.

Final statuses: VERIFIED only for an accepted numeric PASS on a source row with a fresh reference; DIFF for a failed comparison or rejected inspection; NOT VERIFIED for errors, missing references, regression-only rows and unestablished freshness.
