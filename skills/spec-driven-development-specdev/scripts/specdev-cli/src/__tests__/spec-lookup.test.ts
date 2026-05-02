import { describe, expect, test } from "bun:test";
import { mkdirSync, rmSync } from "node:fs";
import { resolve } from "node:path";
import { getAvailableSpecs, lookupSpec } from "../lib/spec-lookup";

const testRoot = resolve(import.meta.dir, "fixtures", "test-project");
const specsDir = resolve(testRoot, ".specs", "active");

// Setup helpers
function setupTestProject(specs: string[]) {
  rmSync(testRoot, { recursive: true, force: true });
  mkdirSync(specsDir, { recursive: true });
  for (const spec of specs) {
    mkdirSync(resolve(specsDir, spec), { recursive: true });
  }
}

function cleanupTestProject() {
  rmSync(testRoot, { recursive: true, force: true });
}

describe("lookupSpec", () => {
  test("returns found result when spec exists", () => {
    setupTestProject(["my-feature"]);

    const result = lookupSpec("my-feature", testRoot);

    expect(result.found).toBe(true);
    if (result.found) {
      expect(result.specDir).toContain("my-feature");
      expect(result.tasksPath).toContain("tasks.yaml");
    }

    cleanupTestProject();
  });

  test("returns not found result when spec missing", () => {
    setupTestProject(["other-feature"]);

    const result = lookupSpec("nonexistent", testRoot);

    expect(result.found).toBe(false);
    if (!result.found) {
      expect(result.errorData.error).toContain("nonexistent");
      expect(result.errorData.availableSpecs).toContain("other-feature");
      expect(result.errorData.specsFound).toBe(true);
    }

    cleanupTestProject();
  });

  test("provides suggestions when no specs directory", () => {
    rmSync(testRoot, { recursive: true, force: true });
    mkdirSync(testRoot, { recursive: true });
    // No .specs directory

    const result = lookupSpec("some-feature", testRoot);

    expect(result.found).toBe(false);
    if (!result.found) {
      expect(result.errorData.specsFound).toBe(false);
      expect(result.errorData.suggestions.length).toBeGreaterThan(0);
    }

    cleanupTestProject();
  });
});

describe("getAvailableSpecs", () => {
  test("returns list of spec directories", () => {
    setupTestProject(["feature-a", "feature-b", "feature-c"]);

    const specs = getAvailableSpecs(testRoot);

    expect(specs).toContain("feature-a");
    expect(specs).toContain("feature-b");
    expect(specs).toContain("feature-c");
    expect(specs).toHaveLength(3);

    cleanupTestProject();
  });

  test("returns empty array when no specs", () => {
    rmSync(testRoot, { recursive: true, force: true });
    mkdirSync(testRoot, { recursive: true });

    const specs = getAvailableSpecs(testRoot);

    expect(specs).toEqual([]);

    cleanupTestProject();
  });
});
