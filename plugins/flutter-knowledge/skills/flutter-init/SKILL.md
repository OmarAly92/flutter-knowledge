---
name: flutter-init
description: Use when initializing or refreshing flutter-knowledge.yaml, detecting project packages, or selecting missing package defaults; explicit initialization also sets up packages in empty starters.
---

# Initialize Flutter Knowledge

Create `flutter-knowledge.yaml` next to the project's `pubspec.yaml`. Inspect declared dependencies, dev dependencies and authored `lib/` source, then fill missing package categories from [package-catalog.json](package-catalog.json). The catalog owns defaults, recognized families and dependency sections. Explicit `/flutter-init` or a request to initialize a new project also adds the selected packages to a confirmed empty starter; established apps retain config-only initialization.

## Run

Read [the configuration contract](references/configuration.md). Resolve the script relative to this skill's installed location and run:

```bash
python3 "<skill-directory>/scripts/init_config.py" --project "<flutter-project>" --bootstrap-empty
```

Requires Python 3.10+ and PyYAML; dependency setup also requires Flutter on PATH. If PyYAML is missing, install it in the agent's tool environment or a virtual environment with `python3 -m pip install -r "<skill-directory>/requirements.txt"`, following the environment's permissions; do not add it to the Flutter app. If commands cannot run, produce the configuration manually and report dependency setup unperformed; do not invent version constraints or claim installation.

When another skill invokes initialization only to obtain missing configuration, omit `--bootstrap-empty`. That implicit discovery does not authorize installing the entire recommended stack. A request explicitly limited to configuration also omits the flag.

The helper:

- Reads direct declarations, including SDK, path and git dependencies, and collects comment/string-aware source evidence. State choices use implementation markers as well as imports; a lone stale import does not choose the state stack. Dependency overrides alone do not establish that a package is in use.
- Keeps existing non-null selections and custom top-level configuration. Fills missing entries and refreshes derived `resolution` metadata. Rewriting YAML preserves values, not formatting or comments.
- Groups companion packages before detecting ambiguity. A single observed implementation can resolve declared alternatives; multiple live stacks stay ambiguous. No majority vote overrides the user's intended choice. If several independent choices match, writes `null` plus candidates instead of silently choosing.
- Uses the catalog's default for every missing category. State tests use `bloc_test` for Bloc/Cubit; for another state backend they use the Flutter test runner until a compatible test helper is explicitly selected.
- Without `--bootstrap-empty`, writes only configuration. With it, also prepares packages only for a confirmed empty starter, as described below. Neither mode writes app code, generates code or migrates architecture.

## Empty starter dependencies

An empty starter has no app code in `lib/`/`test/` (empty/comment-only Dart and `.gitkeep` placeholders are allowed), or only unchanged app/widget-test templates matching the installed Flutter SDK (comments and formatting may differ), with only Flutter's starter dependencies. Additional app code, customized Dart, non-starter packages, declared assets/fonts, overrides or workspace configuration make it ineligible. Unknown template shapes stay config-only; inspect the reported reason instead of forcing an established app through this path.

For an eligible starter, the helper uses one `flutter pub add` operation for the selected package list. Flutter chooses SDK-compatible version constraints and resolves/fetches dependencies. Existing constraints and SDK entries remain unchanged; test packages use the catalog's development section. Built-in strategies and explicit `none` are not package names. Alternative configured choices remain selected. Add only the selected packages, not every family member or incidental generators/companion toolkits. Later feature/core work declares any additional dependencies it actually needs.

The helper saves config first, then refreshes declaration metadata after successful package setup. On solver failure or timeout it restores the original pubspec/lockfile and reports failure; retained config choices support retry. Tool caches may remain. Missing Flutter or blocked package resolution is not successful dependency setup. A rerun with those packages already declared adds no duplicates. Native setup, core implementation and app builds belong to `/flutter-core`, not initialization.

Discovery also records shared widget/component locations, contract entry points, declared assets and observed naming/import counts. It stores locations and evidence rather than a component inventory. Observations never replace the fixed conventions; explicit project_contracts win over discovered paths.

After generation, show whether the project qualified for dependency setup, packages actually added/resolved, recommendations still absent from pubspec and unresolved categories. Resolve ambiguous choices before dependent implementation; an unresolved configuration does not trigger package setup. Existing selections that conflict with the project need a scoped decision, not automatic migration.

## Check an existing configuration

```bash
python3 "<skill-directory>/scripts/init_config.py" --project "<flutter-project>" --check
```

Initialization writes the config even if choices remain unresolved, then returns `1` and lists them. Exit codes: `0` configuration choices are resolved and any attempted package setup succeeded; `1` missing/ambiguous/incompatible choices need attention; `2` invalid input, missing tools/files or failed package setup. `--check` never writes or fetches packages and cannot combine with `--bootstrap-empty`. A successful check does not certify arbitrary package API compatibility or install recommendations.

Then invoke `flutter-knowledge` and the task's skills. Package choices change implementation mechanics, not the conventions or naming.
