import { describe, expect, test } from "bun:test";
import { createOutputContext, getOutputMode, parseCommonArgs } from "../lib/args";

describe("parseCommonArgs", () => {
  test("extracts common arguments from args object", () => {
    const args = {
      root: "/path/to/root",
      plain: true,
      quiet: false,
      otherArg: "value",
    };

    const result = parseCommonArgs(args);

    expect(result.root).toBe("/path/to/root");
    expect(result.plain).toBe(true);
    expect(result.quiet).toBe(false);
  });

  test("handles undefined root", () => {
    const args = {
      plain: false,
      quiet: true,
    };

    const result = parseCommonArgs(args);

    expect(result.root).toBeUndefined();
  });

  test("coerces truthy values to boolean", () => {
    const args = {
      plain: 1,
      quiet: "yes",
    };

    const result = parseCommonArgs(args);

    expect(result.plain).toBe(true);
    expect(result.quiet).toBe(true);
  });

  test("coerces falsy values to boolean", () => {
    const args = {
      plain: 0,
      quiet: "",
    };

    const result = parseCommonArgs(args);

    expect(result.plain).toBe(false);
    expect(result.quiet).toBe(false);
  });

  test("handles undefined plain and quiet", () => {
    const args = {};

    const result = parseCommonArgs(args);

    expect(result.plain).toBe(false);
    expect(result.quiet).toBe(false);
  });
});

describe("getOutputMode", () => {
  test("returns json by default", () => {
    const mode = getOutputMode({ plain: false, quiet: false });
    expect(mode).toBe("json");
  });

  test("returns plain when plain flag set", () => {
    const mode = getOutputMode({ plain: true, quiet: false });
    expect(mode).toBe("plain");
  });

  test("returns quiet-json when quiet flag set", () => {
    const mode = getOutputMode({ plain: false, quiet: true });
    expect(mode).toBe("quiet-json");
  });

  test("returns quiet-plain when both flags set", () => {
    const mode = getOutputMode({ plain: true, quiet: true });
    expect(mode).toBe("quiet-plain");
  });
});

describe("createOutputContext", () => {
  test("creates context with correct flags", () => {
    const ctx = createOutputContext({ plain: true, quiet: false });

    expect(ctx.usePlain).toBe(true);
    expect(ctx.quiet).toBe(false);
  });

  test("json outputs formatted JSON", () => {
    const ctx = createOutputContext({ plain: false, quiet: false });
    const logs: string[] = [];
    const originalLog = console.log;
    console.log = (msg: string) => logs.push(msg);

    ctx.json({ test: "value" });

    console.log = originalLog;
    expect(logs[0]).toContain('"test"');
    expect(logs[0]).toContain('"value"');
    expect(logs[0]).toContain("\n"); // Pretty printed
  });

  test("quietJson outputs compact JSON", () => {
    const ctx = createOutputContext({ plain: false, quiet: true });
    const logs: string[] = [];
    const originalLog = console.log;
    console.log = (msg: string) => logs.push(msg);

    ctx.quietJson({ test: "value" });

    console.log = originalLog;
    expect(logs[0]).toBe('{"test":"value"}');
  });
});
