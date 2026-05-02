import { describe, expect, test } from "bun:test";
import { mkdirSync, rmSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import {
  isError,
  isOk,
  parseYamlSafe,
  readFileSafe,
  readYamlFileSafe,
  unwrap,
  unwrapOr,
  writeFileSafe,
} from "../lib/safe-io";

const testDir = resolve(import.meta.dir, "fixtures", "safe-io-test");

function setup() {
  rmSync(testDir, { recursive: true, force: true });
  mkdirSync(testDir, { recursive: true });
}

function cleanup() {
  rmSync(testDir, { recursive: true, force: true });
}

describe("readFileSafe", () => {
  test("returns content for existing file", () => {
    setup();
    const path = resolve(testDir, "test.txt");
    writeFileSync(path, "hello world");

    const result = readFileSafe(path);

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value).toBe("hello world");
    }

    cleanup();
  });

  test("returns error for non-existent file", () => {
    const result = readFileSafe("/nonexistent/path.txt");

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.message).toContain("not found");
    }
  });
});

describe("parseYamlSafe", () => {
  test("parses valid YAML", () => {
    const result = parseYamlSafe<{ key: string }>("key: value");

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.key).toBe("value");
    }
  });

  test("returns error for invalid YAML", () => {
    const result = parseYamlSafe("invalid: [unclosed");

    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error).toBeInstanceOf(Error);
    }
  });
});

describe("readYamlFileSafe", () => {
  test("reads and parses YAML file", () => {
    setup();
    const path = resolve(testDir, "test.yaml");
    writeFileSync(path, "name: test\nvalue: 42");

    const result = readYamlFileSafe<{ name: string; value: number }>(path);

    expect(result.ok).toBe(true);
    if (result.ok) {
      expect(result.value.name).toBe("test");
      expect(result.value.value).toBe(42);
    }

    cleanup();
  });

  test("returns error for invalid YAML file", () => {
    setup();
    const path = resolve(testDir, "invalid.yaml");
    writeFileSync(path, "invalid: [");

    const result = readYamlFileSafe(path);

    expect(result.ok).toBe(false);

    cleanup();
  });

  test("returns error for non-existent file", () => {
    const result = readYamlFileSafe("/nonexistent.yaml");

    expect(result.ok).toBe(false);
  });
});

describe("writeFileSafe", () => {
  test("writes content to file", () => {
    setup();
    const path = resolve(testDir, "output.txt");

    const result = writeFileSafe(path, "written content");

    expect(result.ok).toBe(true);

    const readResult = readFileSafe(path);
    expect(readResult.ok).toBe(true);
    if (readResult.ok) {
      expect(readResult.value).toBe("written content");
    }

    cleanup();
  });
});

describe("isOk and isError", () => {
  test("isOk returns true for success", () => {
    const result = { ok: true as const, value: "test" };
    expect(isOk(result)).toBe(true);
    expect(isError(result)).toBe(false);
  });

  test("isError returns true for failure", () => {
    const result = { ok: false as const, error: new Error("test") };
    expect(isError(result)).toBe(true);
    expect(isOk(result)).toBe(false);
  });
});

describe("unwrap", () => {
  test("returns value for success", () => {
    const result = { ok: true as const, value: "test" };
    expect(unwrap(result)).toBe("test");
  });

  test("throws for error", () => {
    const result = { ok: false as const, error: new Error("test error") };
    expect(() => unwrap(result)).toThrow("test error");
  });
});

describe("unwrapOr", () => {
  test("returns value for success", () => {
    const result = { ok: true as const, value: "actual" };
    expect(unwrapOr(result, "default")).toBe("actual");
  });

  test("returns default for error", () => {
    const result = { ok: false as const, error: new Error("test") };
    expect(unwrapOr(result, "default")).toBe("default");
  });
});
