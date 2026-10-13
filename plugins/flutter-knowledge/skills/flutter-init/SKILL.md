---
name: flutter-init
description: Use when initializing Flutter Knowledge in a project, creating or updating flutter-knowledge.yaml, detecting the project's packages, or filling missing package choices with the plugin's recommended stack.
---

# Initialize Flutter Knowledge

Create `flutter-knowledge.yaml` next to the project's `pubspec.yaml`. Inspect declared dependencies, dev dependencies and authored `lib/` source, then fill missing package categories from [package-catalog.json](package-catalog.json). The catalog is the single source of package defaults and recognized families. Recommendations are selections for future work, not installed dependencies.

## Run

Read [the configuration contract](references/configuration.md). Resolve the script relative to this skill's installed location and run:

```bash
python3 "<skill-directory>/scripts/init_config.py" --project "<flutter-project>"
```

Requires Python 3.10+ and PyYAML. If PyYAML is missing, install it in the agent's tool environment or a virtual environment with `python3 -m pip install -r "<skill-directory>/requirements.txt"`, following the environment's permissions; do not add it to the Flutter app. If commands cannot run, read the catalog and produce the same configuration manually, disclosing that validation was not run.

The helper:

- Reads direct declarations, including SDK, path and git dependencies, and collects comment/string-aware source evidence. State choices use implementation markers as well as imports; a lone stale import does not choose the state stack. Dependency overrides alone do not establish that a package is in use.
- Keeps existing non-null selections and custom top-level configuration. Fills missing entries and refreshes derived `resolution` metadata. Rewriting YAML preserves values, not formatting or comments.
- Groups companion packages before detecting ambiguity. A single observed implementation can resolve declared alternatives; multiple live stacks stay ambiguous. No majority vote overrides the user's intended choice. If several independent choices match, writes `null` plus candidates instead of silently choosing.
- Uses the catalog's default for every missing category. State tests use `bloc_test` for Bloc/Cubit; for another state backend they use the Flutter test runner until a compatible test helper is explicitly selected.
- Writes only the project config. It does not edit `pubspec.yaml`, fetch packages, add generated code or migrate architecture.

Discovery also records shared widget/component locations, contract entry points, declared assets and observed naming/import counts. It stores locations and evidence rather than a component inventory. Observations never replace the fixed conventions; explicit project_contracts win over discovered paths.

After generation, show the selected packages, the recommendations absent from pubspec, and any unresolved categories. Resolve ambiguous choices with the user before dependent implementation. Existing selections that conflict with the project need a scoped decision, not automatic migration.

## Check an existing configuration

```bash
python3 "<skill-directory>/scripts/init_config.py" --project "<flutter-project>" --check
```

Initialization writes the config even if choices remain unresolved, then returns `1` and lists them. Exit codes: `0` configuration choices are resolved; `1` missing/ambiguous/incompatible choices need attention; `2` invalid input, missing files or inability to run. `--check` never writes. A successful check does not certify arbitrary package API compatibility or install recommendations.

Then invoke `flutter-knowledge` and the task's skills. Package choices change implementation mechanics, not the conventions or naming.
