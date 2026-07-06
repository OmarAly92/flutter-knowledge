# Flutter Knowledge

Flutter/Dart skills for coding agents. Install once and your agent follows a
consistent set of full-stack Flutter conventions — feature architecture, the
data layer, Cubit state management, dependency injection, routing, the core UI
wrappers, and localization — plus an `add-translation` helper for keeping
`en.json` / `ar.json` in sync.

The skills trigger automatically from their `description` — whenever Flutter or
Dart comes up, the agent loads them. Nothing to invoke by hand.

## What's inside

| Skill | Purpose |
| --- | --- |
| **flutter-knowledge** | Full-stack conventions: architecture, data layer, Cubit, DI, routing, UI, styling, localization. |
| **add-translation** | Add localization key(s) to `en.json` and `ar.json` in sync, then regenerate `locale_keys.g.dart`. |

## Install

Install separately for each harness you use. Every method points at the same
`skills/` directory, so updating is always "pull the latest."

### Claude Code

```bash
/plugin marketplace add OmarAly92/flutter-knowledge
/plugin install flutter-knowledge@flutter-skills
```

Update: `/plugin marketplace update flutter-skills`, then reinstall.

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

### Codex / Cursor / Kimi

Add this repo through the harness's plugin/extension manager. Each reads its own
manifest — `.codex-plugin/plugin.json`, `.cursor-plugin/plugin.json`,
`.kimi-plugin/plugin.json` — all of which register `./skills/`.

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
