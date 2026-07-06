# Flutter Knowledge — repo guide

This repository packages Flutter/Dart skills for coding agents and distributes
them to multiple harnesses (Claude Code, Codex, Cursor, Kimi, OpenCode, Pi,
Gemini). It is a distribution wrapper — the actual guidance lives in the skills.

## Single source of truth

All skill content lives in `skills/`:

- `skills/flutter-knowledge/SKILL.md` — full-stack conventions (architecture,
  data layer, Cubit state management, DI, routing, UI wrappers, localization).
- `skills/add-translation/SKILL.md` — add localization keys to `en.json` /
  `ar.json` in sync.

Never duplicate skill text elsewhere. Every harness manifest just points at
`./skills/`. Edit the `SKILL.md` files; the manifests do not change.

## How each harness finds the skills

| Harness | Entry point |
| --- | --- |
| Claude Code | `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` (skills auto-discovered) |
| Codex | `.codex-plugin/plugin.json` (`"skills": "./skills/"`) |
| Cursor | `.cursor-plugin/plugin.json` (`"skills": "./skills/"`) |
| Kimi | `.kimi-plugin/plugin.json` (`"skills": "./skills/"`) |
| OpenCode | `.opencode/plugins/flutter-knowledge.js` (registers `skills/`) |
| Pi | `.pi/extensions/flutter-knowledge.ts` + `package.json` `pi` field |
| Gemini | `gemini-extension.json` → `GEMINI.md` (includes both skills) |
| Any other agent | `install.sh` symlinks `skills/*` into `~/.claude/skills/` |

## Adding a skill

1. Create `skills/<name>/SKILL.md` with `name` + `description` frontmatter.
2. No manifest changes needed — every harness points at the whole `skills/` dir.
3. Bump the version (see below) and push.

## Releasing a new version

Run `./bump-version.sh <x.y.z>` — it rewrites the version string in every
manifest and `version.json` at once. Then commit, tag `vX.Y.Z`, and push.
Consumers update by pulling the repo / re-running their harness's update step.
