import { existsSync, mkdirSync, renameSync } from "node:fs";
import { resolve } from "node:path";
import { defineCommand } from "citty";
import { parseCommonArgs } from "../lib/args";
import { getArchivedDir } from "../lib/project-root";
import { lookupSpec, outputSpecNotFoundError } from "../lib/spec-lookup";
import { getNextTask, parseTasksFile } from "../lib/spec-parser";
import { error, info, success } from "../ui/output";

export const archiveCommand = defineCommand({
  meta: {
    name: "archive",
    description: "Archive a completed spec to .specs/archived/",
  },
  args: {
    spec: {
      type: "positional",
      description: "Spec name to archive",
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
    force: {
      type: "boolean",
      alias: "f",
      description: "Archive even if not 100% complete",
    },
  },
  async run({ args }) {
    const specName = args.spec as string;
    const commonArgs = parseCommonArgs(args);
    const { plain: usePlain, quiet } = commonArgs;
    const force = args.force as boolean;

    const { archivedDir } = getArchivedDir(commonArgs.root);

    // Validate spec exists in active
    const lookup = lookupSpec(specName, commonArgs.root);

    if (!lookup.found) {
      outputSpecNotFoundError(lookup.errorData, usePlain);
    }

    const { specDir } = lookup;

    // Check if spec is 100% complete (unless --force)
    const tasksPath = resolve(specDir, "tasks.yaml");
    if (!force && existsSync(tasksPath)) {
      const phases = parseTasksFile(tasksPath);
      const nextTask = getNextTask(phases);

      if (nextTask) {
        const errorData = {
          error: "Spec is not complete",
          spec: specName,
          nextTask: {
            id: nextTask.id,
            title: nextTask.title,
          },
          hint: "Use --force to archive anyway",
        };

        if (!usePlain) {
          console.log(JSON.stringify(errorData, null, 2));
        } else {
          error("Spec is not complete");
          info(`Next incomplete task: ${nextTask.id} - ${nextTask.title}`);
          console.log();
          info("Use --force to archive anyway");
        }
        process.exit(1);
      }
    }

    // Check if already archived
    const targetDir = resolve(archivedDir, specName);
    if (existsSync(targetDir)) {
      const errorData = {
        error: `Spec '${specName}' already exists in archived`,
        targetPath: targetDir,
      };

      if (!usePlain) {
        console.log(JSON.stringify(errorData, null, 2));
      } else {
        error(`Spec '${specName}' already exists in archived`);
        info(`Target path: ${targetDir}`);
      }
      process.exit(1);
    }

    // Create archived directory if it doesn't exist
    if (!existsSync(archivedDir)) {
      mkdirSync(archivedDir, { recursive: true });
    }

    // Move spec to archived
    renameSync(specDir, targetDir);

    // Output result
    const result = {
      archived: true,
      spec: specName,
      from: specDir,
      to: targetDir,
    };

    // JSON is default
    if (!usePlain && !quiet) {
      console.log(JSON.stringify(result, null, 2));
    } else if (quiet) {
      if (!usePlain) {
        console.log(JSON.stringify({ archived: true, spec: specName }));
      } else {
        console.log(specName);
      }
    } else {
      // Plain human-readable output
      success(`Archived '${specName}'`);
      info(`From: ${specDir}`);
      info(`To: ${targetDir}`);
    }
  },
});
