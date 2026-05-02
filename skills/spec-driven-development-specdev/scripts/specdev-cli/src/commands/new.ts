import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { defineCommand } from "citty";
import { parseCommonArgs } from "../lib/args";
import { getActiveDir } from "../lib/project-root";
import { PLAN_MD, SPEC_MD, TASKS_YAML } from "../templates";
import { error, info, success } from "../ui/output";

function toTitleCase(name: string): string {
  return name
    .split("-")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function applyTemplateSubstitutions(template: string, name: string, titleName: string): string {
  return template
    .replace(/\{Feature Name\}/g, titleName)
    .replace(/feature: feature-name/g, `feature: ${name}`);
}

export const newCommand = defineCommand({
  meta: {
    name: "new",
    description: "Create a new spec from templates",
  },
  args: {
    name: {
      type: "positional",
      description: "Spec name (will create .specs/active/{name}/)",
      required: true,
    },
    root: {
      type: "string",
      alias: "r",
      description: "Project root directory (default: auto-detect)",
    },
    plain: {
      type: "boolean",
      description: "Human-readable output instead of JSON",
    },
    quiet: {
      type: "boolean",
      alias: "q",
      description: "Minimal output",
    },
  },
  async run({ args }) {
    const name = args.name as string;
    const commonArgs = parseCommonArgs(args);
    const { plain: usePlain, quiet } = commonArgs;

    // Validate name (allow kebab-case, alphanumeric, underscores)
    if (!/^[a-z0-9][a-z0-9_-]*$/.test(name)) {
      const errorData = {
        error: "Invalid spec name",
        name,
        hint: "Use lowercase letters, numbers, hyphens, and underscores. Must start with letter or number.",
      };
      if (!usePlain) {
        console.log(JSON.stringify(errorData, null, 2));
      } else {
        error("Invalid spec name");
        info("Use lowercase letters, numbers, hyphens, and underscores.");
        info("Must start with a letter or number.");
      }
      process.exit(1);
    }

    // Get active directory
    const { activeDir, projectRoot, autoDetected } = getActiveDir(commonArgs.root);

    // Check if .specs/active directory exists
    if (!existsSync(activeDir)) {
      const errorData = {
        error: "No .specs/active/ directory found",
        searchedPath: activeDir,
        hint: "Run 'spec init' first to initialize the specs structure",
      };
      if (!usePlain) {
        console.log(JSON.stringify(errorData, null, 2));
      } else {
        error("No .specs/active/ directory found");
        info("Run 'spec init' first to initialize the specs structure");
      }
      process.exit(1);
    }

    // Check if spec already exists
    const specDir = resolve(activeDir, name);
    if (existsSync(specDir)) {
      const errorData = {
        error: `Spec '${name}' already exists`,
        path: specDir,
      };
      if (!usePlain) {
        console.log(JSON.stringify(errorData, null, 2));
      } else {
        error(`Spec '${name}' already exists`);
        info(`Path: ${specDir}`);
      }
      process.exit(1);
    }

    // Create spec directory
    mkdirSync(specDir, { recursive: true });

    // Apply template substitutions
    const titleName = toTitleCase(name);
    const specMd = applyTemplateSubstitutions(SPEC_MD, name, titleName);
    const planMd = applyTemplateSubstitutions(PLAN_MD, name, titleName);
    const tasksYaml = applyTemplateSubstitutions(TASKS_YAML, name, titleName);

    // Write template files
    writeFileSync(resolve(specDir, "spec.md"), specMd);
    writeFileSync(resolve(specDir, "plan.md"), planMd);
    writeFileSync(resolve(specDir, "tasks.yaml"), tasksYaml);

    // Output result
    const result = {
      created: true,
      spec: name,
      path: specDir,
      files: ["spec.md", "plan.md", "tasks.yaml"],
    };

    if (!usePlain && !quiet) {
      console.log(JSON.stringify(result, null, 2));
    } else if (quiet) {
      if (!usePlain) {
        console.log(JSON.stringify({ created: true, spec: name }));
      } else {
        console.log(specDir);
      }
    } else {
      success(`Created spec: ${name}`);
      info(`Path: ${specDir}`);
      console.log();
      info("Next steps:");
      info("  1. Edit spec.md with your requirements");
      info("  2. Fill out plan.md with technical approach");
      info("  3. Define tasks in tasks.yaml");
    }
  },
});
