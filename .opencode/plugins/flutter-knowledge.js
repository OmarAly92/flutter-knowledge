/**
 * Flutter Knowledge plugin for OpenCode.ai
 *
 * Registers this repo's skills/ directory with OpenCode so its SKILL.md files
 * are discovered via description-based triggers, AND force-injects the
 * flutter-knowledge conventions into the system prompt whenever the project
 * has a pubspec.yaml — so the conventions apply even if the model doesn't
 * decide to invoke the skill on its own.
 */

import { existsSync, readFileSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const skillsDir = path.resolve(__dirname, '../../skills');
const flutterSkillPath = path.join(skillsDir, 'flutter-knowledge', 'SKILL.md');

function isFlutterProject(startDir) {
  let dir = startDir;
  for (let i = 0; i < 25; i++) {
    if (existsSync(path.join(dir, 'pubspec.yaml'))) return true;
    const parent = path.dirname(dir);
    if (parent === dir) return false;
    dir = parent;
  }
  return false;
}

function loadSkillBody() {
  const raw = readFileSync(flutterSkillPath, 'utf8');
  return raw.replace(/^---\n[\s\S]*?\n---\n/, '').trim();
}

export const FlutterKnowledgePlugin = async (ctx) => {
  const projectDir = ctx?.directory ?? ctx?.worktree ?? process.cwd();

  return {
    // Inject the skills path into live config so OpenCode discovers the
    // flutter-knowledge skills without manual symlinks or config edits.
    config: async (config) => {
      config.skills = config.skills || {};
      config.skills.paths = config.skills.paths || [];
      if (!config.skills.paths.includes(skillsDir)) {
        config.skills.paths.push(skillsDir);
      }
    },

    'experimental.chat.system.transform': async (input, output) => {
      if (isFlutterProject(projectDir)) {
        output.system.push(loadSkillBody());
      }
    },
  };
};
