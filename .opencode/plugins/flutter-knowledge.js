/**
 * Flutter Knowledge plugin for OpenCode.ai
 *
 * Registers this repo's skills/ directory with OpenCode so its SKILL.md files
 * are discovered. There is no bootstrap injection — the skills load on their
 * own description-based triggers via OpenCode's native `skill` tool.
 */

import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const skillsDir = path.resolve(__dirname, '../../skills');

export const FlutterKnowledgePlugin = async () => {
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
  };
};
