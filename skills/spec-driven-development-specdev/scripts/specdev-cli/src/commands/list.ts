import { existsSync, readdirSync, statSync } from "node:fs";
import { resolve } from "node:path";
import { defineCommand } from "citty";
import { parseCommonArgs } from "../lib/args";
import { calculateProgress } from "../lib/progress";
import { getActiveDir } from "../lib/project-root";
import { parseTasksFile } from "../lib/spec-parser";
import { error, info, note, success, warn } from "../ui/output";

interface SpecStatus {
  name: string;
  path: string;
  progress: {
    total: number;
    done: number;
    remaining: number;
    percent: number;
  };
  suggestArchive: boolean;
}

export const listCommand = defineCommand({
  meta: {
    name: "list",
    description: "List all active specs and their progress",
  },
  args: {
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
    const commonArgs = parseCommonArgs(args);
    const { plain: usePlain, quiet } = commonArgs;

    const { activeDir, specsDir, projectRoot } = getActiveDir(commonArgs.root);

    // Check if .specs/ exists
    if (!existsSync(specsDir)) {
      const errorData = {
        ok: false,
        error: "No .specs/ directory found",
        hint: "Run `spec init` to initialize the project",
      };

      if (!usePlain) {
        console.log(JSON.stringify(errorData, null, 2));
      } else {
        error("No .specs/ directory found");
        info("Run `spec init` to initialize the project");
      }
      process.exit(1);
    }

    // Check if active/ exists
    if (!existsSync(activeDir)) {
      const result = {
        ok: true,
        specsDir,
        specs: [],
        summary: { total: 0, completed: 0, inProgress: 0 },
      };

      if (!usePlain && !quiet) {
        console.log(JSON.stringify(result, null, 2));
      } else if (quiet) {
        if (!usePlain) {
          console.log(JSON.stringify({ ok: true, total: 0 }));
        } else {
          console.log("0 specs");
        }
      } else {
        info("No active specs");
      }
      return;
    }

    // Get all spec directories
    const entries = readdirSync(activeDir);
    const specDirs = entries.filter((name) => {
      const fullPath = resolve(activeDir, name);
      return statSync(fullPath).isDirectory();
    });

    // Gather status for each spec
    const specs: SpecStatus[] = [];
    for (const name of specDirs) {
      const specPath = resolve(activeDir, name);
      const tasksPath = resolve(specPath, "tasks.yaml");

      let progress = { total: 0, done: 0, remaining: 0, percent: 0 };

      if (existsSync(tasksPath)) {
        const phases = parseTasksFile(tasksPath);
        progress = calculateProgress(phases);
      }

      specs.push({
        name,
        path: specPath,
        progress,
        suggestArchive: progress.percent === 100,
      });
    }

    // Sort by progress (lowest first, so incomplete specs are at top)
    specs.sort((a, b) => a.progress.percent - b.progress.percent);

    // Calculate summary
    const completed = specs.filter((s) => s.progress.percent === 100).length;
    const inProgress = specs.length - completed;

    // Output
    const result = {
      ok: true,
      specsDir,
      specs,
      summary: {
        total: specs.length,
        completed,
        inProgress,
      },
    };

    if (!usePlain && !quiet) {
      console.log(JSON.stringify(result, null, 2));
    } else if (quiet) {
      if (!usePlain) {
        console.log(
          JSON.stringify({
            ok: true,
            total: specs.length,
            completed,
            inProgress,
          }),
        );
      } else {
        console.log(`${specs.length} specs (${completed} complete, ${inProgress} in progress)`);
      }
    } else {
      // Human-readable output
      if (specs.length === 0) {
        info("No active specs");
        return;
      }

      console.log();
      console.log(`Active Specs (${specs.length} total)`);
      console.log("─".repeat(50));
      console.log();

      for (const spec of specs) {
        const { name, progress, suggestArchive } = spec;
        const progressStr = `${progress.percent}% (${progress.done}/${progress.total})`;

        // Create padded line
        const dots = ".".repeat(Math.max(3, 40 - name.length - progressStr.length));

        if (suggestArchive) {
          success(`${name} ${dots} ${progressStr} → ready to archive`);
        } else if (progress.percent === 0) {
          info(`${name} ${dots} ${progressStr}`);
        } else {
          console.log(`  ${name} ${dots} ${progressStr}`);
        }
      }

      console.log();

      if (completed > 0) {
        console.log(`Summary: ${completed} completed, ${inProgress} in progress`);
        console.log();
        const completedSpecs = specs.filter((s) => s.suggestArchive).map((s) => s.name);
        note(`Run \`spec archive ${completedSpecs[0]}\` to archive completed specs`);
      } else {
        console.log(`Summary: ${inProgress} in progress`);
      }
    }
  },
});
