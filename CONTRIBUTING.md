# Flutter Knowledge — repo guide

This repository packages Flutter/Dart skills for coding agents and distributes
them to multiple harnesses (Claude Code, Codex, Cursor, Kimi, OpenCode, Pi,
Gemini). It is a distribution wrapper — the actual guidance lives in the skills.

## Single source of truth

The repo holds two plugins, each in `plugins/<name>/` with its own
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
- `plugins/flutter-knowledge/skills/flutter-cubit/SKILL.md` — Cubit + state classes, state naming, data
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
- `plugins/flutter-knowledge/skills/design-from-html-flutter/` — turn an HTML design prototype into skin
  colors, text styles, motion constants, core widgets, and per-screen design
  docs + implementation prompts. The only skill split over several Markdown files: `SKILL.md` is the
  phase index, `playbook.md` holds the extraction code per phase, and
  `templates.md` the doc structures.

`flutter-knowledge` is deliberately small: it holds only the hard rules whose
cost is highest if missed, plus the skill map. Everything else loads on
demand. The five core mini skills (`flutter-feature-structure`,
`flutter-data-layer`, `flutter-cubit`, `flutter-screen-ui`,
`flutter-routing-di`) and the helpers (`drift-local-database`,
`hive-local-database`, `flutter-testing`, `add-translation`,
`flutter-app-theme`, `design-from-html-flutter`) each have their own scoped `description` so the
agent can trigger them directly, and the `flutter-knowledge` map tells the
agent it MUST invoke them (via the Skill tool, or `/<skill-name>`) before
writing the code they cover. The two local-database skills are mutually
exclusive per project — the map picks between them by checking
`pubspec.yaml` for drift vs hive/hive_ce. Likewise the skills teach the `context.tokens` theme layer; a project
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

## flutter-design-handoff

`plugins/flutter-design-handoff/skills/` holds `figma-to-widget`,
`visual-verification` (with `scripts/compare.py`) and `golden-tests`, copied
from Mohamed Draz's `flutter-design-fidelity` (MIT; his notice is in
`plugins/flutter-design-handoff/LICENSE` and must stay), plus
`html-to-widget` (with `scripts/layout-tree.js`). All four follow this
repo's conventions and build on `flutter-knowledge`. They have no hook and
no map row of their own; the `flutter-knowledge` map points at
`html-to-widget` / `figma-to-widget` when they are installed. Otherwise they
load from their descriptions. They ship for Claude Code, Codex and
`install.sh`. After changing `compare.py`, run `python3 tests/test_compare.py`.

## How each harness finds the skills

| Harness | Entry point | Forced? |
| --- | --- | --- |
| Claude Code | `.claude-plugin/marketplace.json` lists both plugins; each has `plugins/<name>/.claude-plugin/plugin.json` (skills auto-discovered) | Yes — `plugins/flutter-knowledge/hooks/hooks.json` runs a `SessionStart` hook |
| Codex | `.agents/plugins/marketplace.json` lists both plugins; each has `plugins/<name>/.codex-plugin/plugin.json` (`"skills": "./skills/"`) | Yes — `flutter-knowledge`'s inline `"hooks"` field runs a `SessionStart` hook |
| Cursor | `.cursor-plugin/plugin.json` (`"skills": "./plugins/flutter-knowledge/skills/"`) | No — description-based only |
| Kimi | `.kimi-plugin/plugin.json` (`"skills": "./plugins/flutter-knowledge/skills/"`) | No — description-based only |
| OpenCode | `.opencode/plugins/flutter-knowledge.js` (registers `plugins/flutter-knowledge/skills/`) | Yes — `experimental.chat.system.transform` hook |
| Pi | `.pi/extensions/flutter-knowledge.ts` + `package.json` `pi` field | Yes — `session_start` + `before_agent_start` hooks |
| Gemini | `gemini-extension.json` → `GEMINI.md` (includes all twelve `flutter-knowledge` skills) | Yes, implicitly — `GEMINI.md` always loads (Gemini has no on-demand mechanism, so the five core mini skills and `drift-local-database`/`hive-local-database`/`flutter-testing`/`add-translation`/`flutter-app-theme`/`design-from-html-flutter` are always included there too, unlike every other harness; `design-from-html-flutter` is multi-file, so its `playbook.md` and `templates.md` get their own `@` includes) |
| Any other agent | `install.sh` symlinks `plugins/*/skills/*` into `~/.claude/skills/` | No — description-based only |

Only Claude Code, Codex and `install.sh` carry `flutter-design-handoff`.

"Forced" means the `flutter-knowledge` map and hard rules (not the five core
mini skills, `drift-local-database`, `hive-local-database`, `flutter-testing`,
`add-translation`, `flutter-app-theme`, or `design-from-html-flutter`, which stay on-demand and are
reached through the map) get injected
whenever the project has a `pubspec.yaml`,
regardless of whether the model would have decided to trigger the skill from
its description. The detection logic and injected content is duplicated
across `plugins/flutter-knowledge/hooks/force-flutter-knowledge.mjs` (Claude Code + Codex),
`.opencode/plugins/flutter-knowledge.js`, and
`.pi/extensions/flutter-knowledge.ts` because each harness's hook API is
shaped differently — but all three read the live
`plugins/flutter-knowledge/skills/flutter-knowledge/SKILL.md` at runtime, so there's nothing to keep in
sync by hand when the skill content changes.

## Adding a skill

1. Create `plugins/flutter-knowledge/skills/<name>/SKILL.md` with `name` + `description` frontmatter.
2. Add a row for it to the skill map in `plugins/flutter-knowledge/skills/flutter-knowledge/SKILL.md`.
3. Add an `@./plugins/flutter-knowledge/skills/<name>/SKILL.md` include to `GEMINI.md`.
4. No manifest changes needed — every harness points at the whole `skills/` dir.
5. Bump the version (see below) and push.

A `flutter-design-handoff` skill goes in
`plugins/flutter-design-handoff/skills/<name>/SKILL.md` and needs only step 5.

## Benchmarking a skill change

Before merging a change to any `SKILL.md`, run the benchmark in `benchmark/`
against `master` (see `benchmark/README.md`, which has a paste-in prompt). It
spawns Sonnet 5.5 agents on a fixture project with legacy traps, grades the
code they write, and compares rule breaks, translations and tokens per version.
Its output goes to `benchmark/out/`, which is not committed.

## Releasing a new version

Run `./bump-version.sh <x.y.z>` — it rewrites the version string in every
manifest and `version.json` at once; both plugins share one version. Then commit, tag `vX.Y.Z`, and push.
Consumers update by pulling the repo / re-running their harness's update step.
