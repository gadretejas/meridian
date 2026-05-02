import { appendFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { basename, resolve } from "node:path";
import { defineCommand } from "citty";
import { PROJECT_MD } from "../templates";
import { info, success } from "../ui/output";

export const initCommand = defineCommand({
  meta: {
    name: "init",
    description: "Initialize .specs/ structure for a project",
  },
  args: {
    plain: {
      type: "boolean",
      description: "Human-readable output instead of JSON",
    },
  },
  async run({ args }) {
    const usePlain = args.plain as boolean;
    const projectName = basename(process.cwd());
    const specDir = resolve(process.cwd(), ".specs");

    const created: string[] = [];
    const existed: string[] = [];

    // Check and create .specs directory
    if (existsSync(specDir)) {
      existed.push(".specs");
    } else {
      mkdirSync(specDir);
      created.push(".specs");
    }

    // Check and create active directory
    const activeDir = resolve(specDir, "active");
    if (existsSync(activeDir)) {
      existed.push(".specs/active");
    } else {
      mkdirSync(activeDir, { recursive: true });
      created.push(".specs/active");
    }

    // Check and create archived directory
    const archivedDir = resolve(specDir, "archived");
    if (existsSync(archivedDir)) {
      existed.push(".specs/archived");
    } else {
      mkdirSync(archivedDir, { recursive: true });
      created.push(".specs/archived");
    }

    // Check and create project.md
    const projectMdPath = resolve(specDir, "project.md");
    if (existsSync(projectMdPath)) {
      existed.push(".specs/project.md");
    } else {
      const projectMd = PROJECT_MD.replace(/\{\{PROJECT_NAME\}\}/g, projectName);
      writeFileSync(projectMdPath, projectMd);
      created.push(".specs/project.md");
    }

    // Update .gitignore if it exists
    const gitignorePath = resolve(process.cwd(), ".gitignore");
    if (existsSync(gitignorePath)) {
      const gitignoreContent = readFileSync(gitignorePath, "utf-8");
      if (!gitignoreContent.includes(".specs/archived")) {
        appendFileSync(
          gitignorePath,
          "\n# Archived specs (optional, can be large)\n# .specs/archived/\n",
        );
      }
    }

    // JSON output (default)
    if (!usePlain) {
      console.log(
        JSON.stringify({
          project: projectName,
          created,
          existed,
        }),
      );
      return;
    }

    // Plain output
    if (created.length === 0) {
      success("Spec structure already initialized");
      return;
    }

    success(`Initialized spec-driven development for: ${projectName}`);
    if (created.length > 0) {
      info(`Created: ${created.join(", ")}`);
    }
    if (existed.length > 0) {
      info(`Already existed: ${existed.join(", ")}`);
    }
    console.log();
    info("Next steps:");
    info("  1. Edit .specs/project.md with your project details");
    info("  2. Create your first spec: specdev new {spec-name}");
  },
});
