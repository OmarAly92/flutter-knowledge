# Flutter Knowledge — repo guide

This repository packages Flutter/Dart skills for coding agents and distributes
them to multiple harnesses (Claude Code, Codex, Cursor, Kimi, OpenCode, Pi,
Gemini). It is a distribution wrapper — the actual guidance lives in the skills.

## Single source of truth

The repo holds one plugin in `plugins/flutter-knowledge/` with its own
`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json` and `skills/`.
All of `flutter-knowledge`'s skill content lives in
`plugins/flutter-knowledge/skills/`:

- `plugins/flutter-knowledge/skills/flutter-knowledge/SKILL.md` — the map: always-on hard rules plus a
  table telling the agent which skill it MUST invoke before writing each kind
  of code.
- `plugins/flutter-knowledge/skills/flutter-feature-structure/SKILL.md` — feature folder tree, `_screen`
  suffix, the `lib/core/` folders, and "read an existing equivalent file first
  and mirror it".
- `plugins/flutter-knowledge/skills/flutter-data-layer/SKILL.md` — models, params, remote data sources,
  repositories, `EndPoints`, `Failure`.
- `plugins/flutter-knowledge/skills/flutter-state-management/SKILL.md` — Cubit + state classes, state naming, data
  and controller lifecycle.
- `plugins/flutter-knowledge/skills/flutter-screen-ui/SKILL.md` — Screen/Body split, widget structure,
  core UI wrappers, colors, text styles, spacing, localization, navigation.
- `plugins/flutter-knowledge/skills/flutter-routing-di/SKILL.md` — routes in `lib/core/router/`,
  `BlocProvider` wiring, per-feature `get_it` injection files
  (`<feature>_injection.dart` + `registerAppDependencies`).
- `plugins/flutter-knowledge/skills/drift-local-database/SKILL.md` — local persistence (drift/SQLite):
  tables, DAOs, entities, migrations, local-only and hybrid repositories.
- `plugins/flutter-knowledge/skills/hive-local-database/SKILL.md` — local persistence (Hive/hive_ce):
  boxes, storage↔model mapping, local-only and hybrid repositories.
- `plugins/flutter-knowledge/skills/flutter-testing/SKILL.md` — unit test conventions: mocktail mocks,
  bloc_test cubit tests, data source/repository/cubit coverage.
- `plugins/flutter-knowledge/skills/add-translation/SKILL.md` — add localization keys to `en.json` /
  `ar.json` in sync.
- `plugins/flutter-knowledge/skills/flutter-app-theme/SKILL.md` — the `lib/core/theme` layer:
  `AppTokens` read as `context.tokens` (skin colors, spacing, radii, text,
  elevation, motion, shapes), skins as a list (built-in + JSON skins in a
  `SkinRegistry`, `SkinCubit.select`), `AppTheme.of(skin)` with the
  `ColorScheme` mapping, when a design's value becomes a token, and
  `scripts/token_audit.py` (after changing it, run
  `python3 tests/test_token_audit.py`).
- `plugins/flutter-knowledge/skills/set-theme-from-html/SKILL.md` — whole-HTML theme/asset application after core, with browser foundation snapshots and explicit-manifest asset imports.
- `flutter-knowledge/references/workflows.md` owns task routes and completion; its
  `design-briefs.md` owns source-neutral planning templates. `html-to-widget/references/source-extraction.md`
  owns HTML foundation extraction. Keep detailed recipes in their owning skill.

`flutter-knowledge` is deliberately small: it holds only the hard rules whose
cost is highest if missed, plus the skill map. Everything else loads on
demand. The five core mini skills (`flutter-feature-structure`,
`flutter-data-layer`, `flutter-state-management`, `flutter-screen-ui`,
`flutter-routing-di`) and the helpers (`flutter-init`, `flutter-core`, `flutter-accessibility-rtl`, `flutter-responsive-layout`,
`flutter-performance`, `flutter-review`, `drift-local-database`,
`hive-local-database`, `flutter-testing`, `add-translation`,
`flutter-app-theme`) each have their own scoped `description` so the
agent can trigger them directly, and the `flutter-knowledge` map tells the
agent it MUST invoke them (via the Skill tool, or `/<skill-name>`) before
writing the code they cover. The two local-database skills are mutually
exclusive per project — the map picks the configured engine, detected from `pubspec.yaml` by `flutter-init`. Likewise the skills teach the `context.tokens` theme layer; a project
without `lib/core/theme/app_tokens.dart` is an older one, and the map,
`flutter-screen-ui` and `flutter-app-theme` each carry one short note telling
the agent to mirror that project's own theme classes instead. Keep old-shape
fallbacks to those three notes. When adding a new on-demand skill,
follow this same pattern rather than inlining it into `flutter-knowledge` —
give it its own scoped `description`, add a row to the map, and do NOT set
`disable-model-invocation: true`, since that flag removes a skill from the
model's invocable-skill list entirely (blocking even the Skill-tool call that
the `flutter-knowledge` map relies on), leaving only explicit slash-command
invocation as a path in.

Never duplicate skill text elsewhere. Every harness manifest just points at a
plugin's `skills/`. Edit the `SKILL.md` files; the manifests do not change.

## Design implementation and visual testing

The same `plugins/flutter-knowledge/skills/` folder holds `figma-to-widget`,
`visual-verification` (with `scripts/compare.py`) and `golden-tests`, adapted
from Mohamed Draz's `flutter-design-fidelity` (MIT; his notice is preserved in
`plugins/flutter-knowledge/LICENSE` and must stay), plus `html-to-widget`
(with `scripts/layout-tree.js`) and `set-theme-from-html` for whole-design foundation/asset application after core. Its focused helpers are checked with `python3 tests/test_html_to_theme.py`; no proprietary font bytes are included in test fixtures. These skills follow the code conventions and
ship on every supported harness. The map points at `html-to-widget` /
`figma-to-widget`; verification and golden tests also load through descriptions
and workflow handoffs. After changing `compare.py`, run
`python3 tests/test_compare.py`.

## How each harness finds the skills

| Harness | Entry point | Forced? |
| --- | --- | --- |
| Claude Code | `.claude-plugin/marketplace.json` lists `flutter-knowledge`; its manifest is `plugins/flutter-knowledge/.claude-plugin/plugin.json` (skills auto-discovered) | Yes — `plugins/flutter-knowledge/hooks/hooks.json` runs a `SessionStart` hook |
| Codex | `.agents/plugins/marketplace.json` lists `flutter-knowledge`; its manifest is `plugins/flutter-knowledge/.codex-plugin/plugin.json` (`"skills": "./skills/"`) | Yes — `flutter-knowledge`'s inline `"hooks"` field runs a `SessionStart` hook |
| Cursor | `.cursor-plugin/plugin.json` (`"skills": "./plugins/flutter-knowledge/skills/"`) | No — description-based only |
| Kimi | `.kimi-plugin/plugin.json` (`"skills": "./plugins/flutter-knowledge/skills/"`) | No — description-based only |
| OpenCode | `.opencode/plugins/flutter-knowledge.js` (registers `plugins/flutter-knowledge/skills/`) | Yes — `experimental.chat.system.transform` hook |
| Pi | `.pi/extensions/flutter-knowledge.ts` + `package.json` `pi` field | Yes — `session_start` + `before_agent_start` hooks |
| Gemini | `gemini-extension.json` → `GEMINI.md` (includes all 22 skills plus their shared workflow and design references) | Yes, implicitly — `GEMINI.md` always loads; Gemini has no on-demand mechanism |
| Any other agent | `install.sh` symlinks `plugins/flutter-knowledge/skills/*` into `~/.claude/skills/` | No — description-based only |

Every supported harness carries all 22 skills.

"Forced" means the `flutter-knowledge` map and hard rules (not the five core
mini skills, `flutter-init`, `flutter-core`, `flutter-accessibility-rtl`, `flutter-responsive-layout`,
`flutter-performance`, `flutter-review`, `drift-local-database`, `hive-local-database`, `flutter-testing`,
`add-translation`, `flutter-app-theme`,
`set-theme-from-html`, `html-to-widget`, `figma-to-widget`, `visual-verification`, or `golden-tests`,
which stay on-demand outside Gemini and load through the map, descriptions
or workflow handoffs) get injected
whenever the project has a `pubspec.yaml`,
regardless of whether the model would have decided to trigger the skill from
its description. The detection logic and injected content is duplicated
across `plugins/flutter-knowledge/hooks/force-flutter-knowledge.mjs` (Claude Code + Codex),
`.opencode/plugins/flutter-knowledge.js`, and
`.pi/extensions/flutter-knowledge.ts` because each harness's hook API is
shaped differently — but all three read the live
`plugins/flutter-knowledge/skills/flutter-knowledge/SKILL.md` at runtime, so there's nothing to keep in
sync by hand when the skill content changes.

After changing harness manifests, discovery hooks, the installer or Gemini
includes, run `python3 tests/test_harness_compatibility.py`. These tests execute
local hook contracts, not live host clients; report runtime skips explicitly.

## Adding a skill

1. Create `plugins/flutter-knowledge/skills/<name>/SKILL.md` with `name` + `description` frontmatter.
2. Add a row for it to the skill map in `plugins/flutter-knowledge/skills/flutter-knowledge/SKILL.md`.
3. Add an `@./plugins/flutter-knowledge/skills/<name>/SKILL.md` include to `GEMINI.md`.
4. No manifest changes needed — every harness points at the whole `skills/` dir.
5. Bump the version (see below) and push.

## Configuration and initialization

`flutter-init` owns `package-catalog.json`, the YAML contract and `scripts/init_config.py`.
Defaults must be edited in the catalog, not repeated in skill files. Source
inspection and the review gate share `flutter-init/scripts/dart_source.py`;
`project_discovery.py` owns observations and locations, never a component inventory. Run
`python3 tests/test_flutter_init.py` after changing detection or initialization.
`flutter-state-management` replaces the old Cubit skill name while retaining the
Dart naming conventions. Its default code examples live in `references/cubit.md`.
Golden capture is shared through `golden-tests/references/capture.md`.
State mechanics are checked with `tests/check_state_references.py`; new recipe
versions must be analyzed and exercised against the installed APIs.

Core implementation assets and theme mapping fragments are checked with
`python3 tests/check_core_references.py` after changes; use `--only cache`,
`--only logger` or `--only theme` for a component. Fixture pins belong in
`tests/fixtures/core-references/manifest.json`, not the package-default catalog.
Python/Node CI checks fixture assembly/reporting and records required Flutter
followup; it does not compile the Dart references.

`flutter-review` is findings-only. Its helper must include untracked app-relative
files, never write formatter output, never initialize config/fetch packages/update
baselines, and report skipped/manual checks. Run `python3 tests/test_flutter_review.py`
after changing it. Accessibility, responsiveness and performance each remain scoped
skills that add responsibilities without replacing the architectural conventions.

## Benchmarking a skill change

Before merging a change to any `SKILL.md`, run the benchmark in `benchmark/`
against `master` (see `benchmark/README.md`, which has a paste-in prompt). It
spawns Sonnet 5.5 agents on a fixture project with legacy traps, grades the
code they write, and compares rule breaks, translations and tokens per version.
Its output goes to `benchmark/out/`, which is not committed.

For description-only changes with unchanged skill bodies and resources, use the
paired discovery probe in `benchmark/README.md` and run
`python3 tests/test_skill_selection.py`. Freeze both catalogs, use identical
requests/model/settings and inspect every miss; record size and preservation
checks separately from end-to-end token usage. Use the documented focused suites
for affected helpers, and relevant implementation benchmark tasks when recipes
or architectural instructions change.

## Releasing a new version

Run `./bump-version.sh <x.y.z>` — it rewrites the version string in every
manifest and `version.json` at once. Then commit, tag `vX.Y.Z`, and push.
Consumers update by pulling the repo / re-running their harness's update step.

After changing source/reference reuse, run `python3 tests/test_design_cache.py`; hits must never imply verified Flutter output. compare.py --json changes reporting only; scoring/settings and exits must match text output. Review --log-dir may write evidence logs only, retaining full failures and unchanged statuses.
