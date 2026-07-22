# Flutter Knowledge

Flutter/Dart skills for coding agents. Install once and your agent follows a
consistent set of full-stack Flutter conventions — feature architecture, the
data layer, Cubit state management, dependency injection, routing, the core UI
wrappers, and localization — plus five on-demand helpers: `add-translation`
for keeping `en.json` / `ar.json` in sync, `drift-local-database` and
`hive-local-database` for local persistence (drift/SQLite or Hive),
`flutter-testing` for mocktail/bloc_test unit tests, and
`design-from-html-flutter` for building the app's design system from an HTML
prototype.

`flutter-knowledge` triggers automatically from its `description` — whenever
Flutter or Dart comes up, the agent loads it. Nothing to invoke by hand. The
helpers are lazy-loaded instead: they stay out of `flutter-knowledge`
and only enter context on demand, either because the agent recognizes the
task needs one from its own scoped `description` (local storage, tests, a
missing translation key, an HTML design prototype), because
`flutter-knowledge` explicitly invokes it,
or because you run `/add-translation`, `/drift-local-database`,
`/hive-local-database`, `/flutter-testing`, or `/design-from-html-flutter`
directly — this keeps `flutter-knowledge` itself smaller and avoids loading
storage/localization/testing/design conventions into every session.

On Claude Code, Codex, OpenCode, and Pi, `flutter-knowledge` is also
force-loaded: a hook/plugin checks for `pubspec.yaml` and injects the
conventions directly, so they apply even if the model doesn't decide to
trigger the skill on its own. The timing differs by harness, though — Claude
Code and Codex inject it once, at session start (a `SessionStart` hook); on
OpenCode and Pi it's re-applied to the system prompt on every turn instead,
since those harnesses only expose per-turn hooks (`experimental.chat.system.transform`
and `before_agent_start` respectively) — it doesn't accumulate across turns,
and system prompts are typically prompt-cached, but it's a different
mechanism from the other two's one-time injection. Gemini already gets this
for free since `GEMINI.md` is always loaded. Cursor and Kimi rely on
description-based triggering only (see `CONTRIBUTING.md`).

## What's inside

| Skill | Purpose | Loads |
| --- | --- | --- |
| **flutter-knowledge** | Full-stack conventions: architecture, data layer, Cubit, DI, routing, UI, styling, localization. | Automatically |
| **drift-local-database** | Drift/SQLite local persistence: tables, DAOs, entities, migrations, local-only and hybrid repositories. | On demand, via `flutter-knowledge` or `/drift-local-database` |
| **hive-local-database** | Hive (hive_ce) local persistence: boxes, storage↔model mapping, local-only and hybrid repositories. | On demand, via `flutter-knowledge` or `/hive-local-database` |
| **flutter-testing** | Unit test conventions: mocktail mocks, bloc_test cubit tests, data source/repository/cubit coverage. | On demand, via `flutter-knowledge` or `/flutter-testing` |
| **add-translation** | Add localization key(s) to `en.json` and `ar.json` in sync, then regenerate `locale_keys.g.dart`. | On demand, via `flutter-knowledge` or `/add-translation` |
| **design-from-html-flutter** | Turn an HTML design prototype into skin colors, text styles, motion constants, core widgets, and per-screen design docs + implementation prompts. | On demand, via `flutter-knowledge` or `/design-from-html-flutter` |

## Install

Install separately for each harness you use. Every method points at the same
`skills/` directory, so updating is always "pull the latest."

### Claude Code

```bash
/plugin marketplace add OmarAly92/flutter-knowledge
/plugin install flutter-knowledge@flutter-skills
```

Update: run both of these — the first refreshes the marketplace metadata, the second actually pulls the new version in.

```bash
/plugin marketplace update flutter-skills
/plugin install flutter-knowledge@flutter-skills
```

### Gemini CLI

```bash
gemini extensions install https://github.com/OmarAly92/flutter-knowledge
```

Update: `gemini extensions update flutter-knowledge`.

### OpenCode

Add to your `opencode.json`:

```json
{
  "plugin": ["flutter-knowledge@git+https://github.com/OmarAly92/flutter-knowledge.git"]
}
```

See [`.opencode/INSTALL.md`](./.opencode/INSTALL.md) for details. Update: `git pull` / clear the package cache.

### Pi

Install the package (its `package.json` exposes the Pi extension and skills):

```bash
pi package add github:OmarAly92/flutter-knowledge
```

### Codex

Add this repo through Codex's plugin manager; it reads `.codex-plugin/plugin.json`,
which registers `./skills/` and — like Claude Code — wires up the `SessionStart`
hook that force-loads `flutter-knowledge` for Flutter projects.

### Cursor / Kimi

Add this repo through the harness's plugin/extension manager. Each reads its own
manifest — `.cursor-plugin/plugin.json`, `.kimi-plugin/plugin.json` — which
registers `./skills/`. Unlike Codex, these two are description-based triggering
only; no hook is wired up.

### Any other agent (universal fallback)

For any agent that reads `SKILL.md` files from `~/.claude/skills/`:

```bash
git clone https://github.com/OmarAly92/flutter-knowledge.git
cd flutter-knowledge
./install.sh
```

This symlinks each skill into `~/.claude/skills/` (override with
`CLAUDE_SKILLS_DIR=/path ./install.sh`). Update with `git pull` and re-run
`./install.sh`.

## Repo structure

`skills/` is the single source of truth. Every harness manifest is a thin
adapter that points at it — see [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the full map and
how to add a skill or cut a release.

## License

MIT — see [`LICENSE`](./LICENSE).
