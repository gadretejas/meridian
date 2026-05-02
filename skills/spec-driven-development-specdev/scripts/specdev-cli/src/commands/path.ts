import { existsSync } from "node:fs";
import { resolve } from "node:path";
import { defineCommand } from "citty";
import { parseCommonArgs } from "../lib/args";
import { type DependencyAnalysis, analyzeDependencies } from "../lib/dependency-graph";
import { getAvailableSpecs, lookupSpec, outputSpecNotFoundError } from "../lib/spec-lookup";
import { parseTasksFile } from "../lib/spec-parser";
import { info, printDivider, printHeader, success, warn } from "../ui/output";

export const pathCommand = defineCommand({
  meta: {
    name: "path",
    description: "Analyze task dependencies and show critical path",
  },
  args: {
    feature: {
      type: "positional",
      description: "Spec name to analyze",
      required: false,
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
      description: "Minimal output (critical path only)",
    },
  },
  async run({ args }) {
    const commonArgs = parseCommonArgs(args);
    const { plain: usePlain, quiet } = commonArgs;

    // If no spec specified, list available specs
    if (!args.feature) {
      const specs = getAvailableSpecs(commonArgs.root);

      if (!usePlain) {
        console.log(JSON.stringify({ availableSpecs: specs }));
        return;
      }

      console.log("Usage: spec path {spec-name}");
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

    const spec = args.feature as string;
    const lookup = lookupSpec(spec, commonArgs.root);

    if (!lookup.found) {
      outputSpecNotFoundError(lookup.errorData, usePlain);
    }

    const { specDir } = lookup;
    const tasksPath = resolve(specDir, "tasks.yaml");

    if (!existsSync(tasksPath)) {
      const errorData = { error: "No tasks.yaml found", spec, path: tasksPath };
      if (!usePlain) {
        console.log(JSON.stringify(errorData, null, 2));
      } else {
        warn("No tasks.yaml found");
      }
      process.exit(1);
    }

    const phases = parseTasksFile(tasksPath);
    const analysis: DependencyAnalysis = analyzeDependencies(phases);

    // Build output data
    const data = {
      spec,
      ...analysis,
    };

    // Output - JSON is default
    if (!usePlain && !quiet) {
      console.log(JSON.stringify(data, null, 2));
      return;
    }

    // Quiet mode
    if (quiet) {
      if (!usePlain) {
        console.log(
          JSON.stringify({
            criticalPath: analysis.criticalPath,
            parallelizable: analysis.parallelizable,
          }),
        );
      } else {
        if (analysis.criticalPath.length > 0) {
          console.log(`Critical path: ${analysis.criticalPath.join(" → ")}`);
        } else {
          console.log("No critical path (all complete or no dependencies)");
        }
        if (analysis.parallelizable.length > 0) {
          console.log(`Parallelizable: ${analysis.parallelizable.join(", ")}`);
        }
      }
      return;
    }

    // Plain output
    printHeader(`DEPENDENCY ANALYSIS: ${spec}`);

    printDivider("OVERVIEW");
    info(`Tasks: ${analysis.completedTasks}/${analysis.totalTasks} complete`);

    printDivider("CRITICAL PATH");
    if (analysis.criticalPath.length > 0) {
      console.log(`  ${analysis.criticalPath.join(" → ")}`);
      info(`Length: ${analysis.criticalPath.length} tasks`);
    } else {
      success("No critical path - all tasks complete or no dependencies");
    }

    printDivider("PARALLELIZABLE");
    if (analysis.parallelizable.length > 0) {
      info("These tasks can be worked on in parallel:");
      for (const taskId of analysis.parallelizable) {
        console.log(`  - ${taskId}`);
      }
    } else {
      info("No tasks available for parallel work");
    }

    printDivider("BLOCKED TASKS");
    if (analysis.blocked.length > 0) {
      for (const b of analysis.blocked) {
        console.log(`  ${b.task}: ${b.title}`);
        console.log(`    Blocked by: ${b.blockedBy.join(", ")}`);
      }
    } else {
      success("No blocked tasks");
    }

    printDivider("PHASE GATES");
    if (analysis.phaseGates.length > 0) {
      for (const gate of analysis.phaseGates) {
        console.log(`  Phase ${gate.phase} (${gate.name}):`);
        console.log(`    Waiting on: ${gate.waitingOn.join(", ")}`);
      }
    } else {
      info("No phase gates blocking progress");
    }

    console.log();
    console.log("═".repeat(60));
  },
});
