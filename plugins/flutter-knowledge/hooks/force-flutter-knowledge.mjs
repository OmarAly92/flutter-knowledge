#!/usr/bin/env node
// SessionStart hook (Claude Code + Codex share this file — both harnesses use
// the same stdin JSON input and hookSpecificOutput.additionalContext schema).
// Detects a Flutter project (pubspec.yaml anywhere above cwd) and, if found,
// force-injects skills/flutter-knowledge/SKILL.md as session context instead
// of relying on the model to trigger the skill from its description.

import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const scriptDir = dirname(fileURLToPath(import.meta.url));
const skillPath = resolve(scriptDir, '..', 'skills', 'flutter-knowledge', 'SKILL.md');

function readStdin() {
  try {
    return readFileSync(0, 'utf8');
  } catch {
    return '';
  }
}

function findProjectRoot(startDir) {
  let dir = startDir;
  for (let i = 0; i < 25; i++) {
    if (existsSync(join(dir, 'pubspec.yaml'))) return dir;
    const parent = dirname(dir);
    if (parent === dir) return null;
    dir = parent;
  }
  return null;
}

function loadSkillBody() {
  const raw = readFileSync(skillPath, 'utf8');
  return raw.replace(/^---\n[\s\S]*?\n---\n/, '').trim();
}

let input = {};
try {
  input = JSON.parse(readStdin() || '{}');
} catch {
  input = {};
}

const cwd = input.cwd || process.cwd();

if (findProjectRoot(cwd)) {
  const additionalContext =
    'This is a Flutter project (pubspec.yaml detected). The following ' +
    'Flutter/Dart conventions are the source of truth for this session — ' +
    'apply them to any .dart file or pubspec.yaml work, overriding default ' +
    'behavior and any conflicting legacy patterns in the codebase:\n\n' +
    loadSkillBody();

  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'SessionStart',
        additionalContext,
      },
    }),
  );
}
