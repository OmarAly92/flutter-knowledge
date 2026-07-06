# Installing Flutter Knowledge for OpenCode

## Prerequisites

- [OpenCode.ai](https://opencode.ai) installed

## Installation

Add the plugin to the `plugin` array in your `opencode.json` (global or project-level):

```json
{
  "plugin": ["flutter-knowledge@git+https://github.com/OmarAly92/flutter-knowledge.git"]
}
```

Restart OpenCode. The plugin registers the `skills/` directory, so OpenCode's
native `skill` tool can discover `flutter-knowledge` and `add-translation`.

Verify by asking OpenCode to list its skills.

## Usage

Use OpenCode's native `skill` tool:

```
use skill tool to list skills
use skill tool to load flutter-knowledge
```

## Updating

OpenCode installs through a git-backed package spec. Some OpenCode/Bun versions
pin the resolved git dependency, so a restart may not pick up the newest commit.
If updates do not appear, clear OpenCode's package cache or reinstall the plugin.

To pin a specific version:

```json
{
  "plugin": ["flutter-knowledge@git+https://github.com/OmarAly92/flutter-knowledge.git#v1.0.0"]
}
```
