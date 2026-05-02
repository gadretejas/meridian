import { existsSync, readFileSync, readdirSync } from "node:fs";
import { resolve } from "node:path";
import { defineCommand } from "citty";
import { parseCheckpoint } from "../lib/checkpoint-parser";
import { calculateProgressFromCounts } from "../lib/progress";
import { getActiveDir } from "../lib/project-root";
import { getAvailableSpecs, lookupSpec, outputSpecNotFoundError } from "../lib/spec-lookup";
import { countCheckboxes, getNextTask, parseTasksFile } from "../lib/spec-parser";
import type { Phase, Task } from "../types";
import { info, printDivider, printHeader, warn } from "../ui/output";

type Level = "min" | "standard" | "full";

interface PhaseInfo {
  current: number;
  total: number;
  name: string;
}

function getCurrentPhase(phases: Phase[], currentTask: Task | null): PhaseInfo | null {
  if (phases.length === 0) return null;

  if (currentTask) {
    const phase = phases.find((p) => p.number === currentTask.phase);
    return phase
      ? { current: phase.number, total: phases.length, name: phase.name }
      : { current: currentTask.phase, total: phases.length, name: "Unknown" };
  }

  const lastPhase = phases[phases.length - 1];
  return { current: lastPhase.number, total: phases.length, name: lastPhase.name };
}

function getNextTaskAfterCurrent(phases: Phase[], currentTask: Task | null): Task | null {
  if (!currentTask) return null;

  let foundCurrent = false;
  for (const phase of phases) {
    for (const task of phase.tasks) {
      if (foundCurrent) {
        const hasIncomplete = task.subtasks.some((s) => !s.completed);
        if (hasIncomplete) return task;
      }
      if (task.id === currentTask.id) {
        foundCurrent = true;
      }
    }
  }
  return null;
}

function parseLevel(value: string | undefined): Level {
  if (value === "min" || value === "standard" || value === "full") {
    return value;
  }
  return "standard";
}

export const contextCommand = defineCommand({
  meta: {
    name: "context",
    description: "Show spec context for AI consumption",
  },
  args: {
    spec: {
      type: "positional",
      description: "Spec name",
      required: false,
    },
    level: {
      type: "string",
      alias: "l",
      description: "Context level: min (task only), standard (default), full (all details)",
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
  },
  async run({ args }) {
    const usePlain = args.plain as boolean;
    const level = parseLevel(args.level as string | undefined);
    const root = args.root as string | undefined;
    const { specsDir, projectRoot, autoDetected } = getActiveDir(root);

    // If no spec specified, list available specs
    if (!args.spec) {
      const specs = getAvailableSpecs(root);

      if (!usePlain) {
        console.log(JSON.stringify({ availableSpecs: specs, specsDir, projectRoot, autoDetected }));
        return;
      }

      console.log("Usage: spec context {spec-name} [--level min|standard|full]");
      console.log();
      console.log("Available specs:");
      if (specs.length === 0) {
        info("(none)");
      } else {
        for (const s of specs) {
          info(`  ${s}`);
        }
      }
      return;
    }

    const specName = args.spec as string;
    const lookup = lookupSpec(specName, root);

    if (!lookup.found) {
      outputSpecNotFoundError(lookup.errorData, usePlain);
    }

    const { specDir } = lookup;

    // Parse tasks
    const tasksPath = resolve(specDir, "tasks.yaml");
    let phases: ReturnType<typeof parseTasksFile> = [];
    let progress: { done: number; total: number; remaining: number; percent: number } | null = null;

    if (existsSync(tasksPath)) {
      const tasksContent = readFileSync(tasksPath, "utf-8");
      const { total, done } = countCheckboxes(tasksContent);
      if (total > 0) {
        progress = calculateProgressFromCounts(total, done);
      }
      phases = parseTasksFile(tasksPath);
    }

    const currentTask = getNextTask(phases);
    const allComplete = !currentTask;
    const phaseInfo = getCurrentPhase(phases, currentTask);
    const upcomingTask = getNextTaskAfterCurrent(phases, currentTask);

    // Build response based on level
    type TaskData = {
      id: string;
      title: string;
      files: string[];
      depends?: string[];
      subtasks?: { text: string; completed: boolean; type: string }[];
      notes?: string;
    };

    const data: {
      spec: string;
      level: Level;
      phase: PhaseInfo | null;
      progress: { done: number; total: number; percent: number } | null;
      currentTask: TaskData | null;
      nextTask: { id: string; title: string } | null;
      checkpoint?: {
        date: string | null;
        summary: string | null;
        accomplished: string[];
        blockers: string[];
      } | null;
      phases?: { number: number; name: string; taskCount: number }[];
      specFiles?: string[];
      allComplete: boolean;
      archiveSuggestion?: string;
    } = {
      spec: specName,
      level,
      phase: phaseInfo,
      progress: progress
        ? { done: progress.done, total: progress.total, percent: progress.percent }
        : null,
      currentTask: null,
      nextTask: null,
      allComplete,
    };

    // Current task (all levels)
    if (currentTask) {
      data.currentTask = {
        id: currentTask.id,
        title: currentTask.title,
        files: currentTask.files,
      };

      // Standard and full: add subtasks and depends
      if (level !== "min") {
        data.currentTask.depends = currentTask.depends;
        data.currentTask.subtasks = currentTask.subtasks.map((s) => ({
          text: s.text,
          completed: s.completed,
          type: s.type,
        }));
      }

      // Full: add notes
      if (level === "full" && currentTask.notes) {
        data.currentTask.notes = currentTask.notes;
      }

      // Next task preview
      if (upcomingTask) {
        data.nextTask = { id: upcomingTask.id, title: upcomingTask.title };
      }
    } else {
      data.archiveSuggestion = `spec archive ${specName}`;
    }

    // Checkpoint (standard and full)
    if (level !== "min") {
      const checkpointPath = resolve(specDir, "checkpoint.md");
      if (existsSync(checkpointPath)) {
        const content = readFileSync(checkpointPath, "utf-8");
        const parsed = parseCheckpoint(content);
        data.checkpoint = {
          date: parsed.date,
          summary: parsed.summary,
          accomplished: parsed.accomplished,
          blockers: parsed.blockers,
        };
      }
    }

    // Full: add phases and spec files
    if (level === "full") {
      data.phases = phases.map((p) => ({
        number: p.number,
        name: p.name,
        taskCount: p.tasks.length,
      }));
      data.specFiles = readdirSync(specDir).filter((f) => f.endsWith(".md") || f.endsWith(".yaml"));
    }

    // Output - JSON is default
    if (!usePlain) {
      console.log(JSON.stringify(data, null, 2));
      return;
    }

    // Human-readable output
    printHeader(`CONTEXT: ${specName} (${level})`);

    // Phase and progress
    if (data.phase) {
      info(`Phase ${data.phase.current}/${data.phase.total}: ${data.phase.name}`);
    }
    if (data.progress) {
      info(`Progress: ${data.progress.done}/${data.progress.total} (${data.progress.percent}%)`);
    }

    // Current task
    printDivider("CURRENT TASK");
    if (data.currentTask) {
      console.log(`  ${data.currentTask.id}: ${data.currentTask.title}`);
      if (data.currentTask.files.length > 0) {
        console.log(`  Files: ${data.currentTask.files.join(", ")}`);
      }
      if (data.currentTask.depends && data.currentTask.depends.length > 0) {
        console.log(`  Depends: ${data.currentTask.depends.join(", ")}`);
      }
      if (data.currentTask.subtasks && data.currentTask.subtasks.length > 0) {
        console.log("  Subtasks:");
        for (const subtask of data.currentTask.subtasks) {
          const check = subtask.completed ? "[x]" : "[ ]";
          const typeTag = subtask.type !== "impl" ? ` [${subtask.type}]` : "";
          console.log(`    ${check} ${subtask.text}${typeTag}`);
        }
      }
    } else {
      info("All tasks complete!");
      info(`Suggestion: ${data.archiveSuggestion}`);
    }

    // Next task preview
    if (data.nextTask) {
      printDivider("NEXT");
      console.log(`  ${data.nextTask.id}: ${data.nextTask.title}`);
    }

    // Checkpoint (standard/full)
    if (data.checkpoint) {
      printDivider("CHECKPOINT");
      if (data.checkpoint.date) {
        info(`Date: ${data.checkpoint.date}`);
      }
      if (data.checkpoint.summary) {
        info(data.checkpoint.summary);
      }
      if (data.checkpoint.blockers.length > 0) {
        console.log("  Blockers:");
        for (const b of data.checkpoint.blockers) {
          console.log(`    ⚠ ${b}`);
        }
      }
    }

    // Phases (full only)
    if (data.phases) {
      printDivider("ALL PHASES");
      for (const phase of data.phases) {
        console.log(`  Phase ${phase.number}: ${phase.name} (${phase.taskCount} tasks)`);
      }
    }

    // Spec files (full only)
    if (data.specFiles) {
      printDivider("FILES");
      for (const f of data.specFiles) {
        info(`  ${f}`);
      }
    }

    console.log();
  },
});
