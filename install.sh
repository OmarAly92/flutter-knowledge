#!/usr/bin/env bash
#
# Universal installer: symlink every plugin's skills into the agent skills dir.
# Works for any agent that reads SKILL.md files from ~/.claude/skills/.
# Override the target with CLAUDE_SKILLS_DIR=/some/path ./install.sh
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET="${CLAUDE_SKILLS_DIR:-$HOME/.claude/skills}"

mkdir -p "$TARGET"

for retired_skill in flutter-cubit design-from-html-flutter; do
  legacy_link="$TARGET/$retired_skill"
  if [ -L "$legacy_link" ]; then
    case "$(readlink "$legacy_link")" in
      "$REPO_DIR/plugins/flutter-knowledge/skills/$retired_skill"|"$REPO_DIR/skills/$retired_skill") rm -f "$legacy_link" ;;
    esac
  fi
done

count=0
for dir in "$REPO_DIR"/plugins/flutter-knowledge/skills/*/; do
  [ -d "$dir" ] || continue
  name="$(basename "$dir")"
  link="$TARGET/$name"
  if [ -e "$link" ] && [ ! -L "$link" ]; then
    echo "skip $name: $link exists and is not a symlink"
    continue
  fi
  if [ -L "$link" ] && [ -e "$link" ]; then
    case "$(readlink "$link")" in
      "$REPO_DIR"/*) ;;
      *)
        echo "skip $name: $link points outside this repo"
        continue
        ;;
    esac
  fi
  rm -f "$link"
  ln -s "${dir%/}" "$link"
  echo "linked $name -> $link"
  count=$((count + 1))
done

echo "Installed $count skill(s) into $TARGET."
echo "Restart your agent to pick them up."
