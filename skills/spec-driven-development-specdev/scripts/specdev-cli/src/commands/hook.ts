import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { defineCommand } from "citty";
import { calculateProgress } from "../lib/progress";
import { getActiveDir } from "../lib/project-root";
import { getNextTask, parseTasksFile } from "../lib/spec-parser";
import { validateFeature } from "../lib/validator";

/**
 * Parse stdin JSON (Claude Code passes hook data this way)
 * Returns empty object if stdin is a TTY (manual execution) or invalid
 */
async function parseStdinJson(): Promise<Record<string, unknown>> {
  // Skip stdin reading if running interactively (no piped input)
  if (process.stdin.isTTY) {
    return {};
  }

  try {
    const chunks: Buffer[] = [];
    for await (const chunk of process.stdin) {
      chunks.push(chunk);
    }
    const input = Buffer.concat(chunks).toString("utf-8");
    if (!input.trim()) return {};
    return JSON.parse(input);
  } catch {
    return {};
  }
}

/**
 * Hook: session-start
 * Check for active specs, output context of first one
 */
const sessionStartCommand = defineCommand({
  meta: {
    name: "session-start",
    description: "SessionStart hook - show context of first active spec",
  },
  async run() {
    // Consume stdin (required by hook protocol)
    await parseStdinJson();

    const { activeDir } = getActiveDir();

    if (!existsSync(activeDir)) {
      return; // Silent exit - no active specs
    }

    const entries = readdirSync(activeDir);
    const specDirs = entries.filter((name) => {
      const fullPath = resolve(activeDir, name);
      return statSync(fullPath).isDirectory();
    });

    if (specDirs.length === 0) {
      return; // Silent exit - no active specs
    }

    // Get first spec
    const specName = specDirs[0];
    const specDir = resolve(activeDir, specName);
    const tasksPath = resolve(specDir, "tasks.yaml");

    if (!existsSync(tasksPath)) {
      return; // Silent exit - no tasks.yaml
    }

    // Parse tasks and get progress
    const phases = parseTasksFile(tasksPath);
    const progress = calculateProgress(phases);
    const currentTask = getNextTask(phases);

    // Output context
    console.log(`[specdev] Active spec: ${specName}`);
    console.log(`  Progress: ${progress.done}/${progress.total} tasks (${progress.percent}%)`);

    if (currentTask) {
      console.log(`  Current: ${currentTask.id} - ${currentTask.title}`);
      if (currentTask.files.length > 0) {
        console.log(`  Files: ${currentTask.files.join(", ")}`);
      }
    } else {
      console.log(`  Status: All tasks complete - run \`spec archive ${specName}\``);
    }
  },
});

/**
 * Hook: post-edit
 * Read file_path from stdin, validate if it's a tasks.yaml
 */
const postEditCommand = defineCommand({
  meta: {
    name: "post-edit",
    description: "PostToolUse hook - validate tasks.yaml after edit",
  },
  async run() {
    const data = await parseStdinJson();

    // Extract file path from tool input
    const toolInput = data.tool_input as Record<string, unknown> | undefined;
    const filePath = toolInput?.file_path as string | undefined;

    if (!filePath) {
      return; // Silent exit - no file path
    }

    // Only validate tasks.yaml files
    if (!filePath.endsWith("tasks.yaml")) {
      return; // Silent exit - not a tasks.yaml
    }

    // Get spec directory (parent of tasks.yaml)
    const specDir = dirname(filePath);

    if (!existsSync(specDir)) {
      return; // Silent exit - directory doesn't exist
    }

    // Validate the spec
    const result = validateFeature(specDir);

    if (!result.ok) {
      console.log("[specdev] Validation errors:");
      for (const err of result.errors) {
        console.log(`  ✗ ${err.message}`);
      }
      // Exit code 2 = blocking error (per Claude Code hooks spec)
      process.exit(2);
    }

    // Silent exit on success - no need to output anything
  },
});

/**
 * Hook: stop
 * Show progress summary for all active specs
 */
const stopCommand = defineCommand({
  meta: {
    name: "stop",
    description: "Stop hook - show progress summary",
  },
  async run() {
    // Consume stdin (required by hook protocol)
    await parseStdinJson();

    const { activeDir } = getActiveDir();

    if (!existsSync(activeDir)) {
      return; // Silent exit - no active specs
    }

    const entries = readdirSync(activeDir);
    const specDirs = entries.filter((name) => {
      const fullPath = resolve(activeDir, name);
      return statSync(fullPath).isDirectory();
    });

    if (specDirs.length === 0) {
      return; // Silent exit - no active specs
    }

    // Gather progress for each spec
    const specProgress: { name: string; done: number; total: number; percent: number }[] = [];

    for (const name of specDirs) {
      const specDir = resolve(activeDir, name);
      const tasksPath = resolve(specDir, "tasks.yaml");

      if (existsSync(tasksPath)) {
        const phases = parseTasksFile(tasksPath);
        const progress = calculateProgress(phases);
        specProgress.push({
          name,
          done: progress.done,
          total: progress.total,
          percent: progress.percent,
        });
      }
    }

    if (specProgress.length === 0) {
      return; // Silent exit - no specs with tasks
    }

    // Output progress summary
    console.log("[specdev] Session progress:");
    for (const spec of specProgress) {
      if (spec.percent === 100) {
        console.log(
          `  ${spec.name}: ${spec.done}/${spec.total} tasks (${spec.percent}%) → run \`spec archive ${spec.name}\``,
        );
      } else {
        console.log(`  ${spec.name}: ${spec.done}/${spec.total} tasks (${spec.percent}%)`);
      }
    }
  },
});

/**
 * Main hook command with subcommands
 */
export const hookCommand = defineCommand({
  meta: {
    name: "hook",
    description: "Claude Code hook handlers (cross-platform)",
  },
  subCommands: {
    "session-start": sessionStartCommand,
    "post-edit": postEditCommand,
    stop: stopCommand,
  },
});
