import { describe, expect, test } from "bun:test";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { validateFeature, validateSpecMd, validateTasksYaml } from "../lib/validator";
import { addError, addInfo, addWarning, createValidationResult } from "../types";

const testDir = resolve(import.meta.dir, "fixtures", "test-spec");

// Setup and teardown helpers
function setupTestSpec(files: Record<string, string>) {
  rmSync(testDir, { recursive: true, force: true });
  mkdirSync(testDir, { recursive: true });
  for (const [name, content] of Object.entries(files)) {
    writeFileSync(resolve(testDir, name), content);
  }
}

function cleanupTestSpec() {
  rmSync(testDir, { recursive: true, force: true });
}

describe("ValidationResult helpers", () => {
  test("createValidationResult returns clean state", () => {
    const result = createValidationResult();

    expect(result.ok).toBe(true);
    expect(result.errors).toHaveLength(0);
    expect(result.warnings).toHaveLength(0);
    expect(result.info).toHaveLength(0);
  });

  test("addError sets ok to false and adds error", () => {
    const result = createValidationResult();
    addError(result, "Test error", "file.ts");

    expect(result.ok).toBe(false);
    expect(result.errors).toHaveLength(1);
    expect(result.errors[0].message).toBe("Test error");
    expect(result.errors[0].file).toBe("file.ts");
    expect(result.errors[0].severity).toBe("error");
  });

  test("addWarning does not change ok status", () => {
    const result = createValidationResult();
    addWarning(result, "Test warning");

    expect(result.ok).toBe(true);
    expect(result.warnings).toHaveLength(1);
    expect(result.warnings[0].severity).toBe("warning");
  });

  test("addInfo adds info message", () => {
    const result = createValidationResult();
    addInfo(result, "Test info");

    expect(result.ok).toBe(true);
    expect(result.info).toHaveLength(1);
    expect(result.info[0].severity).toBe("info");
  });
});

describe("validateSpecMd", () => {
  test("adds error when spec.md is missing", () => {
    const result = createValidationResult();
    validateSpecMd("/nonexistent/path/spec.md", result);

    expect(result.ok).toBe(false);
    expect(result.errors[0].message).toContain("Missing required file");
  });

  test("validates required sections", () => {
    setupTestSpec({
      "spec.md": `# Spec
## Purpose
Some purpose.
## User Stories
Some stories.
## Requirements
Some requirements SHALL be met.`,
    });

    const result = createValidationResult();
    validateSpecMd(resolve(testDir, "spec.md"), result);

    // Should pass with all required sections
    expect(result.ok).toBe(true);
    expect(result.warnings.filter((w) => w.message.includes("missing"))).toHaveLength(0);

    cleanupTestSpec();
  });

  test("warns about missing sections", () => {
    setupTestSpec({
      "spec.md": "# Just a title\nSome content.",
    });

    const result = createValidationResult();
    validateSpecMd(resolve(testDir, "spec.md"), result);

    // Should have warnings for missing sections
    expect(result.warnings.some((w) => w.message.includes("Purpose"))).toBe(true);
    expect(result.warnings.some((w) => w.message.includes("User Stor"))).toBe(true);
    expect(result.warnings.some((w) => w.message.includes("Requirement"))).toBe(true);

    cleanupTestSpec();
  });

  test("warns about missing acceptance criteria", () => {
    setupTestSpec({
      "spec.md": "# Spec\nNo acceptance criteria here.",
    });

    const result = createValidationResult();
    validateSpecMd(resolve(testDir, "spec.md"), result);

    expect(result.warnings.some((w) => w.message.includes("acceptance criteria"))).toBe(true);

    cleanupTestSpec();
  });

  test("warns about missing formal requirements", () => {
    setupTestSpec({
      "spec.md": "# Spec\nNo formal requirements here.",
    });

    const result = createValidationResult();
    validateSpecMd(resolve(testDir, "spec.md"), result);

    expect(result.warnings.some((w) => w.message.includes("SHALL/MUST"))).toBe(true);

    cleanupTestSpec();
  });

  test("adds word count info", () => {
    setupTestSpec({
      "spec.md": "one two three four five",
    });

    const result = createValidationResult();
    validateSpecMd(resolve(testDir, "spec.md"), result);

    expect(result.info.some((i) => i.message.includes("words"))).toBe(true);

    cleanupTestSpec();
  });
});

describe("validateTasksYaml", () => {
  test("warns when tasks.yaml is missing", () => {
    const result = createValidationResult();
    const taskIds = validateTasksYaml("/nonexistent/path/tasks.yaml", result);

    expect(taskIds).toHaveLength(0);
    expect(result.warnings.some((w) => w.message.includes("Missing tasks.yaml"))).toBe(true);
  });

  test("errors on invalid YAML syntax", () => {
    setupTestSpec({
      "tasks.yaml": "invalid: yaml: [unclosed",
    });

    const result = createValidationResult();
    const taskIds = validateTasksYaml(resolve(testDir, "tasks.yaml"), result);

    expect(result.ok).toBe(false);
    expect(result.errors.some((e) => e.message.includes("Invalid YAML"))).toBe(true);
    expect(taskIds).toHaveLength(0);

    cleanupTestSpec();
  });

  test("errors when phases array is missing", () => {
    setupTestSpec({
      "tasks.yaml": "feature: test\nname: no phases",
    });

    const result = createValidationResult();
    const taskIds = validateTasksYaml(resolve(testDir, "tasks.yaml"), result);

    expect(result.ok).toBe(false);
    expect(result.errors.some((e) => e.message.includes("phases"))).toBe(true);

    cleanupTestSpec();
  });

  test("validates phase structure", () => {
    setupTestSpec({
      "tasks.yaml": `
phases:
  - name: Phase without ID
    tasks:
      - id: "1.1"
        title: Task
        subtasks:
          - text: Do something
            done: false
`,
    });

    const result = createValidationResult();
    validateTasksYaml(resolve(testDir, "tasks.yaml"), result);

    expect(result.errors.some((e) => e.message.includes("missing 'id'"))).toBe(true);

    cleanupTestSpec();
  });

  test("returns task IDs", () => {
    setupTestSpec({
      "tasks.yaml": `
phases:
  - id: 1
    name: Phase 1
    tasks:
      - id: "1.1"
        title: Task One
        subtasks:
          - text: Do it
            done: false
      - id: "1.2"
        title: Task Two
        subtasks:
          - text: Do it
            done: false
`,
    });

    const result = createValidationResult();
    const taskIds = validateTasksYaml(resolve(testDir, "tasks.yaml"), result);

    expect(taskIds).toContain("1.1");
    expect(taskIds).toContain("1.2");

    cleanupTestSpec();
  });

  test("validates dependencies reference existing tasks", () => {
    setupTestSpec({
      "tasks.yaml": `
phases:
  - id: 1
    name: Phase 1
    tasks:
      - id: "1.1"
        title: Task One
        depends:
          - "nonexistent"
        subtasks:
          - text: Do it
            done: false
`,
    });

    const result = createValidationResult();
    validateTasksYaml(resolve(testDir, "tasks.yaml"), result);

    expect(result.errors.some((e) => e.message.includes("invalid dependency"))).toBe(true);

    cleanupTestSpec();
  });

  test("reports progress info", () => {
    setupTestSpec({
      "tasks.yaml": `
phases:
  - id: 1
    name: Phase 1
    tasks:
      - id: "1.1"
        title: Task
        subtasks:
          - text: Done
            done: true
          - text: Not done
            done: false
`,
    });

    const result = createValidationResult();
    validateTasksYaml(resolve(testDir, "tasks.yaml"), result);

    expect(result.info.some((i) => i.message.includes("1/2 subtasks"))).toBe(true);

    cleanupTestSpec();
  });
});

describe("validateFeature", () => {
  test("errors when spec directory does not exist", () => {
    const result = validateFeature("/nonexistent/spec/dir");

    expect(result.ok).toBe(false);
    expect(result.errors[0].message).toContain("not found");
  });

  test("validates complete spec directory", () => {
    setupTestSpec({
      "spec.md": `# Feature
## Purpose
Test purpose.
## User Stories
Test stories.
## Requirements
System SHALL work.

Acceptance Criteria:
- Works
`,
      "tasks.yaml": `
phases:
  - id: 1
    name: Phase 1
    tasks:
      - id: "1.1"
        title: Task
        files:
          - src/file.ts
        subtasks:
          - text: Do it
            done: false
`,
    });

    const result = validateFeature(testDir);

    expect(result.ok).toBe(true);

    cleanupTestSpec();
  });
});
