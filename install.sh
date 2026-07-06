#!/usr/bin/env bash
#
# Universal installer: symlink this repo's skills into the agent skills dir.
# Works for any agent that reads SKILL.md files from ~/.claude/skills/.
# Override the target with CLAUDE_SKILLS_DIR=/some/path ./install.sh
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

mkdir -p "$TARGET"

count=0
for dir in "$REPO_DIR"/skills/*/; do
  [ -d "$dir" ] || continue
  name="$(basename "$dir")"
  link="$TARGET/$name"
  rm -rf "$link"
  ln -s "${dir%/}" "$link"
  echo "linked $name -> $link"
  count=$((count + 1))
done

echo "Installed $count skill(s) into $TARGET."
echo "Restart your agent to pick them up."
