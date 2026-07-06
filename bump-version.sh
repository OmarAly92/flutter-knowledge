#!/usr/bin/env bash
#
# Bump the version string across every manifest at once.
# Usage: ./bump-version.sh <x.y.z>
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEW="${1:-}"

if [ -z "$NEW" ]; then
  echo "usage: ./bump-version.sh <new-version>   (e.g. ./bump-version.sh 1.0.1)"
  exit 1
fi

if ! echo "$NEW" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$'; then
  echo "error: version must be semver x.y.z (got '$NEW')"
  exit 1
fi

FILES=(
  ".claude-plugin/plugin.json"
  ".claude-plugin/marketplace.json"
  ".codex-plugin/plugin.json"
  ".cursor-plugin/plugin.json"
  ".kimi-plugin/plugin.json"
  "gemini-extension.json"
  "package.json"
  "version.json"
)

for f in "${FILES[@]}"; do
  path="$REPO_DIR/$f"
  [ -f "$path" ] || { echo "skip (missing): $f"; continue; }
  perl -0pi -e "s/\"version\":\s*\"[0-9]+\.[0-9]+\.[0-9]+\"/\"version\": \"$NEW\"/g" "$path"
  echo "updated $f -> $NEW"
done

echo
echo "All manifests set to $NEW."
echo "Next: git commit -am \"Release v$NEW\" && git tag v$NEW && git push --follow-tags"
