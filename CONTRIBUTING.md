# Flutter Knowledge — repo guide

This repository packages Flutter/Dart skills for coding agents and distributes
them to multiple harnesses (Claude Code, Codex, Cursor, Kimi, OpenCode, Pi,
Gemini). It is a distribution wrapper — the actual guidance lives in the skills.

## Single source of truth

All skill content lives in `skills/`:

- `skills/flutter-knowledge/SKILL.md` — full-stack conventions (architecture,
  data layer, Cubit state management, DI, routing, UI wrappers, localization).
- `skills/drift-local-database/SKILL.md` — local persistence (drift/SQLite):
  tables, DAOs, entities, migrations, local-only and hybrid repositories.
- `skills/hive-local-database/SKILL.md` — local persistence (Hive/hive_ce):
  boxes, storage↔model mapping, local-only and hybrid repositories.
- `skills/flutter-testing/SKILL.md` — unit test conventions: mocktail mocks,
  bloc_test cubit tests, data source/repository/cubit coverage.
- `skills/add-translation/SKILL.md` — add localization keys to `en.json` /
  `ar.json` in sync.
- `skills/design-from-html-flutter/` — turn an HTML design prototype into skin
  colors, text styles, motion constants, core widgets, and per-screen design
  docs + implementation prompts. The only multi-file skill: `SKILL.md` is the
  phase index, `playbook.md` holds the extraction code per phase, and
  `templates.md` the doc structures.

`drift-local-database`, `hive-local-database`, `flutter-testing`,
`add-translation`, and `design-from-html-flutter` stay out of
`flutter-knowledge` entirely and load on demand
instead — each has its own scoped `description` so the agent can trigger it
directly, and `flutter-knowledge` also carries a short pointer telling the
agent to invoke them (via the Skill tool, or `/drift-local-database` /
`/hive-local-database` / `/flutter-testing` / `/add-translation`) when the task
actually needs local storage, tests, or a new translation key. The two
local-database skills are mutually exclusive per project — `flutter-knowledge`
picks between them by checking `pubspec.yaml` for drift vs hive/hive_ce. This keeps `flutter-knowledge` itself small; the
detailed conventions only enter context when they're relevant. When adding a
new on-demand helper skill, follow this same pattern rather than inlining it
into `flutter-knowledge` — give it its own scoped `description` and do NOT
set `disable-model-invocation: true`, since that flag removes a skill from
the model's invocable-skill list entirely (blocking even the Skill-tool call
that `flutter-knowledge`'s own pointer relies on), leaving only explicit
slash-command invocation as a path in.

Never duplicate skill text elsewhere. Every harness manifest just points at
`./skills/`. Edit the `SKILL.md` files; the manifests do not change.

## How each harness finds the skills

| Harness | Entry point | Forced? |
| --- | --- | --- |
| Claude Code | `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` (skills auto-discovered) | Yes — `hooks/hooks.json` runs a `SessionStart` hook |
| Codex | `.codex-plugin/plugin.json` (`"skills": "./skills/"`) | Yes — inline `"hooks"` field runs a `SessionStart` hook |
| Cursor | `.cursor-plugin/plugin.json` (`"skills": "./skills/"`) | No — description-based only |
| Kimi | `.kimi-plugin/plugin.json` (`"skills": "./skills/"`) | No — description-based only |
| OpenCode | `.opencode/plugins/flutter-knowledge.js` (registers `skills/`) | Yes — `experimental.chat.system.transform` hook |
| Pi | `.pi/extensions/flutter-knowledge.ts` + `package.json` `pi` field | Yes — `session_start` + `before_agent_start` hooks |
| Gemini | `gemini-extension.json` → `GEMINI.md` (includes all six skills) | Yes, implicitly — `GEMINI.md` always loads (Gemini has no on-demand mechanism, so `drift-local-database`/`hive-local-database`/`flutter-testing`/`add-translation`/`design-from-html-flutter` are always included there too, unlike every other harness; `design-from-html-flutter` is multi-file, so its `playbook.md` and `templates.md` get their own `@` includes) |
| Any other agent | `install.sh` symlinks `skills/*` into `~/.claude/skills/` | No — description-based only |

"Forced" means the `flutter-knowledge` conventions (not `drift-local-database`,
`hive-local-database`, `flutter-testing`, `add-translation`, or
`design-from-html-flutter`, which stay on-demand) get injected
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
2. No manifest changes needed — every harness points at the whole `skills/` dir.
3. Bump the version (see below) and push.

## Releasing a new version

Run `./bump-version.sh <x.y.z>` — it rewrites the version string in every
manifest and `version.json` at once. Then commit, tag `vX.Y.Z`, and push.
Consumers update by pulling the repo / re-running their harness's update step.
