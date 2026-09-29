# Flutter Knowledge — repo guide

This repository packages Flutter/Dart skills for coding agents and distributes
them to multiple harnesses (Claude Code, Codex, Cursor, Kimi, OpenCode, Pi,
Gemini). It is a distribution wrapper — the actual guidance lives in the skills.

## Single source of truth

All skill content lives in `skills/`:

- `skills/flutter-knowledge/SKILL.md` — the map: always-on hard rules plus a
  table telling the agent which skill it MUST invoke before writing each kind
  of code.
- `skills/flutter-feature-structure/SKILL.md` — feature folder tree, `_screen`
  suffix, and "read an existing equivalent file first and mirror it".
- `skills/flutter-data-layer/SKILL.md` — models, params, remote data sources,
  repositories, `EndPoints`, `Failure`.
- `skills/flutter-cubit/SKILL.md` — Cubit + state classes, state naming, data
  and controller lifecycle.
- `skills/flutter-screen-ui/SKILL.md` — Screen/Body split, widget structure,
  core UI wrappers, colors, text styles, spacing, localization, navigation.
- `skills/flutter-routing-di/SKILL.md` — routes, `BlocProvider` wiring,
  `get_it` service-locator setup.
- `skills/drift-local-database/SKILL.md` — local persistence (drift/SQLite):
  tables, DAOs, entities, migrations, local-only and hybrid repositories.
- `skills/hive-local-database/SKILL.md` — local persistence (Hive/hive_ce):
  boxes, storage↔model mapping, local-only and hybrid repositories.
- `skills/flutter-testing/SKILL.md` — unit test conventions: mocktail mocks,
  bloc_test cubit tests, data source/repository/cubit coverage.
- `skills/add-translation/SKILL.md` — add localization keys to `en.json` /
  `ar.json` in sync.
- `skills/flutter-app-skin/SKILL.md` — colors and light/dark themes for
  projects with an `AppSkin`: `context.skin`, adding slots, `SkinCubit`,
  `SkinScope`, `AppThemes.fromSkin` and the `ColorScheme` mapping.
- `skills/design-from-html-flutter/` — turn an HTML design prototype into skin
  colors, text styles, motion constants, core widgets, and per-screen design
  docs + implementation prompts. The only multi-file skill: `SKILL.md` is the
  phase index, `playbook.md` holds the extraction code per phase, and
  `templates.md` the doc structures.

`flutter-knowledge` is deliberately small: it holds only the hard rules whose
cost is highest if missed, plus the skill map. Everything else loads on
demand. The five core mini skills (`flutter-feature-structure`,
`flutter-data-layer`, `flutter-cubit`, `flutter-screen-ui`,
`flutter-routing-di`) and the helpers (`drift-local-database`,
`hive-local-database`, `flutter-testing`, `add-translation`,
`flutter-app-skin`, `design-from-html-flutter`) each have their own scoped `description` so the
agent can trigger them directly, and the `flutter-knowledge` map tells the
agent it MUST invoke them (via the Skill tool, or `/<skill-name>`) before
writing the code they cover. The two local-database skills are mutually
exclusive per project — the map picks between them by checking
`pubspec.yaml` for drift vs hive/hive_ce. Likewise `flutter-app-skin` applies
only when the project has `lib/core/app_themes/colors/app_skin.dart`; the map
and `flutter-screen-ui` fall back to `AppColors` otherwise. When adding a new on-demand skill,
follow this same pattern rather than inlining it into `flutter-knowledge` —
give it its own scoped `description`, add a row to the map, and do NOT set
`disable-model-invocation: true`, since that flag removes a skill from the
model's invocable-skill list entirely (blocking even the Skill-tool call that
the `flutter-knowledge` map relies on), leaving only explicit slash-command
invocation as a path in.

Never duplicate skill text elsewhere. Every harness manifest just points at
`./skills/`. Edit the `SKILL.md` files; the manifests do not change.

## How each harness finds the skills

| Harness | Entry point | Forced? |
| --- | --- | --- |
| Claude Code | `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` (skills auto-discovered) | Yes — `hooks/hooks.json` runs a `SessionStart` hook |
| Codex | `.codex-plugin/plugin.json` (`"skills": "./skills/"`) + `.agents/plugins/marketplace.json` | Yes — inline `"hooks"` field runs a `SessionStart` hook |
| Cursor | `.cursor-plugin/plugin.json` (`"skills": "./skills/"`) | No — description-based only |
| Kimi | `.kimi-plugin/plugin.json` (`"skills": "./skills/"`) | No — description-based only |
| OpenCode | `.opencode/plugins/flutter-knowledge.js` (registers `skills/`) | Yes — `experimental.chat.system.transform` hook |
| Pi | `.pi/extensions/flutter-knowledge.ts` + `package.json` `pi` field | Yes — `session_start` + `before_agent_start` hooks |
| Gemini | `gemini-extension.json` → `GEMINI.md` (includes all twelve skills) | Yes, implicitly — `GEMINI.md` always loads (Gemini has no on-demand mechanism, so the five core mini skills and `drift-local-database`/`hive-local-database`/`flutter-testing`/`add-translation`/`flutter-app-skin`/`design-from-html-flutter` are always included there too, unlike every other harness; `design-from-html-flutter` is multi-file, so its `playbook.md` and `templates.md` get their own `@` includes) |
| Any other agent | `install.sh` symlinks `skills/*` into `~/.claude/skills/` | No — description-based only |

"Forced" means the `flutter-knowledge` map and hard rules (not the five core
mini skills, `drift-local-database`, `hive-local-database`, `flutter-testing`,
`add-translation`, `flutter-app-skin`, or `design-from-html-flutter`, which stay on-demand and are
reached through the map) get injected
whenever the project has a `pubspec.yaml`,
regardless of whether the model would have decided to trigger the skill from
its description. The detection logic and injected content is duplicated
across `hooks/force-flutter-knowledge.mjs` (Claude Code + Codex),
`.opencode/plugins/flutter-knowledge.js`, and
`.pi/extensions/flutter-knowledge.ts` because each harness's hook API is
shaped differently — but all three read the live
`skills/flutter-knowledge/SKILL.md` at runtime, so there's nothing to keep in
sync by hand when the skill content changes.

## Adding a skill

1. Create `skills/<name>/SKILL.md` with `name` + `description` frontmatter.
2. Add a row for it to the skill map in `skills/flutter-knowledge/SKILL.md`.
3. Add an `@./skills/<name>/SKILL.md` include to `GEMINI.md`.
4. No manifest changes needed — every harness points at the whole `skills/` dir.
5. Bump the version (see below) and push.

## Benchmarking a skill change

Before merging a change to any `SKILL.md`, run the benchmark in `benchmark/`
against `master` (see `benchmark/README.md`, which has a paste-in prompt). It
spawns Sonnet 5.5 agents on a fixture project with legacy traps, grades the
code they write, and compares rule breaks, translations and tokens per version.
Its output goes to `benchmark/out/`, which is not committed.

## Releasing a new version

Run `./bump-version.sh <x.y.z>` — it rewrites the version string in every
manifest and `version.json` at once. Then commit, tag `vX.Y.Z`, and push.
Consumers update by pulling the repo / re-running their harness's update step.
