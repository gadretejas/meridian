import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  countCheckboxes,
  getNextTask,
  parseTasksContent,
  parseTasksFile,
} from "../lib/spec-parser";

const fixturesDir = resolve(import.meta.dir, "fixtures");

describe("parseTasksContent", () => {
  test("parses valid YAML into phases", () => {
    const yaml = readFileSync(resolve(fixturesDir, "valid-tasks.yaml"), "utf-8");
    const phases = parseTasksContent(yaml);

    expect(phases).toHaveLength(2);
    expect(phases[0].number).toBe(1);
    expect(phases[0].name).toBe("Setup Phase");
    expect(phases[0].tasks).toHaveLength(2);
  });

  test("extracts task properties correctly", () => {
    const yaml = readFileSync(resolve(fixturesDir, "valid-tasks.yaml"), "utf-8");
    const phases = parseTasksContent(yaml);
    const firstTask = phases[0].tasks[0];

    expect(firstTask.id).toBe("1.1");
    expect(firstTask.title).toBe("First Task");
    expect(firstTask.files).toEqual(["src/file.ts", "src/other.ts"]);
    expect(firstTask.depends).toEqual([]);
    expect(firstTask.subtasks).toHaveLength(2);
  });

  test("converts subtask done field to completed", () => {
    const yaml = readFileSync(resolve(fixturesDir, "valid-tasks.yaml"), "utf-8");
    const phases = parseTasksContent(yaml);
    const subtasks = phases[0].tasks[0].subtasks;

    expect(subtasks[0].completed).toBe(false);
    expect(subtasks[1].completed).toBe(true);
  });

  test("handles task dependencies", () => {
    const yaml = readFileSync(resolve(fixturesDir, "valid-tasks.yaml"), "utf-8");
    const phases = parseTasksContent(yaml);
    const secondTask = phases[0].tasks[1];

    expect(secondTask.depends).toEqual(["1.1"]);
  });

  test("handles task flags (parallel, blocked)", () => {
    const yaml = readFileSync(resolve(fixturesDir, "valid-tasks.yaml"), "utf-8");
    const phases = parseTasksContent(yaml);
    const parallelTask = phases[1].tasks[0];

    expect(parallelTask.flags.parallel).toBe(true);
    expect(parallelTask.flags.blocked).toBe(false);
  });

  test("returns empty array for invalid YAML syntax", () => {
    const phases = parseTasksContent("invalid: yaml: [");
    expect(phases).toEqual([]);
  });

  test("returns empty array for empty content", () => {
    const phases = parseTasksContent("");
    expect(phases).toEqual([]);
  });

  test("returns empty array for YAML without phases", () => {
    const phases = parseTasksContent("feature: test\nname: something");
    expect(phases).toEqual([]);
  });
});

describe("parseTasksFile", () => {
  test("reads and parses file from path", () => {
    const phases = parseTasksFile(resolve(fixturesDir, "valid-tasks.yaml"));

    expect(phases).toHaveLength(2);
    expect(phases[0].tasks[0].id).toBe("1.1");
  });
});

describe("getNextTask", () => {
  test("returns first incomplete task", () => {
    const yaml = readFileSync(resolve(fixturesDir, "valid-tasks.yaml"), "utf-8");
    const phases = parseTasksContent(yaml);
    const nextTask = getNextTask(phases);

    expect(nextTask).not.toBeNull();
    expect(nextTask?.id).toBe("1.1");
    expect(nextTask?.title).toBe("First Task");
  });

  test("skips completed tasks", () => {
    const yaml = `
feature: test
phases:
  - id: 1
    name: Phase 1
    tasks:
      - id: "1.1"
        title: Complete Task
        subtasks:
          - text: Done
            done: true
      - id: "1.2"
        title: Incomplete Task
        subtasks:
          - text: Not done
            done: false
`;
    const phases = parseTasksContent(yaml);
    const nextTask = getNextTask(phases);

    expect(nextTask?.id).toBe("1.2");
  });

  test("returns null when all tasks complete", () => {
    const yaml = readFileSync(resolve(fixturesDir, "all-complete-tasks.yaml"), "utf-8");
    const phases = parseTasksContent(yaml);
    const nextTask = getNextTask(phases);

    expect(nextTask).toBeNull();
  });

  test("returns null for empty phases", () => {
    const nextTask = getNextTask([]);
    expect(nextTask).toBeNull();
  });
});

describe("countCheckboxes", () => {
  test("counts done and total subtasks", () => {
    const yaml = readFileSync(resolve(fixturesDir, "valid-tasks.yaml"), "utf-8");
    const { total, done } = countCheckboxes(yaml);

    expect(total).toBe(5);
    expect(done).toBe(3);
  });

  test("returns zeros for all complete", () => {
    const yaml = readFileSync(resolve(fixturesDir, "all-complete-tasks.yaml"), "utf-8");
    const { total, done } = countCheckboxes(yaml);

    expect(total).toBe(2);
    expect(done).toBe(2);
  });

  test("returns zeros for invalid YAML syntax", () => {
    const { total, done } = countCheckboxes("invalid: [");
    expect(total).toBe(0);
    expect(done).toBe(0);
  });

  test("returns zeros for empty content", () => {
    const { total, done } = countCheckboxes("");

    expect(total).toBe(0);
    expect(done).toBe(0);
  });
});
