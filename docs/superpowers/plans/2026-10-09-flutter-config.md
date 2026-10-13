# Flutter configuration implementation plan

Goal: keep the existing conventions while selecting package mechanics through a project-local flutter-knowledge.yaml.

## Scope

- Rename flutter-cubit to flutter-state-management; keep the existing Cubit implementation as the default reference and retain its naming and state/data ownership rules.
- Add flutter-init with a deterministic Python/PyYAML initializer and one package catalog.
- Detect declared packages, fill absent categories with the current stack's recommendations, preserve existing selections, and expose ambiguity without installing or migrating packages.
- Make every skill load the configuration contract before using package-specific examples. Keep Drift and Hive separate.
- Preserve the feature tree, Screen/Body composition, route-owned provisioning, per-method State names, payload-free success states, controller-owned data, nullable models, params naming, token policy and translation completeness.
- Update discovery, docs and the decision map. No release, commit or push is part of this task.

## Work

1. Write integration tests for initialization on blank, existing, ambiguous and customized projects. Verify failure before implementing the helper.
2. Implement safe YAML loading, package-family detection, defaults, merge behavior and read-only checking. Keep recommendations distinct from declared dependencies.
3. Write the configuration contract and package adaptation reference; update skill instructions without changing convention choices.
4. Validate script behavior, skill metadata, references, installer, hooks, benchmark discovery and existing suites. Run bounded independent behavioral checks. The full pre-merge benchmark remains a release gate.
