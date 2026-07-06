import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const extensionDir = dirname(fileURLToPath(import.meta.url));
const skillsDir = resolve(extensionDir, "../..", "skills");

/**
 * Flutter Knowledge extension for Pi.
 *
 * Registers this repo's skills/ directory so Pi discovers the flutter-knowledge
 * and add-translation SKILL.md files. No bootstrap injection — the skills load
 * on their own description-based triggers.
 */
export default function flutterKnowledgePiExtension(pi: ExtensionAPI) {
  pi.on("resources_discover", async () => ({
    skillPaths: [skillsDir],
  }));
}
