import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { existsSync, readFileSync } from "node:fs";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const extensionDir = dirname(fileURLToPath(import.meta.url));
const skillsDir = resolve(extensionDir, "../..", "skills");
const flutterSkillPath = join(skillsDir, "flutter-knowledge", "SKILL.md");

function isFlutterProject(startDir: string): boolean {
  let dir = startDir;
  for (let i = 0; i < 25; i++) {
    if (existsSync(join(dir, "pubspec.yaml"))) return true;
    const parent = dirname(dir);
    if (parent === dir) return false;
    dir = parent;
  }
  return false;
}

function loadSkillBody(): string {
  const raw = readFileSync(flutterSkillPath, "utf8");
  return raw.replace(/^---\n[\s\S]*?\n---\n/, "").trim();
}

/**
 * Flutter Knowledge extension for Pi.
 *
 * Registers this repo's skills/ directory so Pi discovers the flutter-knowledge
 * and add-translation SKILL.md files via description-based triggers, AND
 * force-injects the flutter-knowledge conventions into the system prompt
 * whenever the workspace has a pubspec.yaml — so the conventions apply even
 * if the model doesn't decide to invoke the skill on its own.
 */
export default function flutterKnowledgePiExtension(pi: ExtensionAPI) {
  pi.on("resources_discover", async () => ({
    skillPaths: [skillsDir],
  }));

  let isFlutter = false;

  pi.on("session_start", async (_event, ctx) => {
    isFlutter = isFlutterProject(ctx.cwd);
  });

  pi.on("before_agent_start", async (event) => {
    if (!isFlutter) return;
    return {
      systemPrompt: `${event.systemPrompt}\n\n${loadSkillBody()}`,
    };
  });
}
