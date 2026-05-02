import { describe, expect, test } from "bun:test";
import { calculateProgress, calculateProgressFromCounts } from "../lib/progress";
import type { Phase } from "../types";

describe("calculateProgressFromCounts", () => {
  test("calculates percentage correctly", () => {
    const result = calculateProgressFromCounts(10, 3);

    expect(result.total).toBe(10);
    expect(result.done).toBe(3);
    expect(result.remaining).toBe(7);
    expect(result.percent).toBe(30);
  });

  test("handles zero total", () => {
    const result = calculateProgressFromCounts(0, 0);

    expect(result.total).toBe(0);
    expect(result.done).toBe(0);
    expect(result.remaining).toBe(0);
    expect(result.percent).toBe(0);
  });

  test("handles 100% complete", () => {
    const result = calculateProgressFromCounts(5, 5);

    expect(result.remaining).toBe(0);
    expect(result.percent).toBe(100);
  });

  test("rounds percentage to nearest integer", () => {
    // 1/3 = 33.33...%
    const result = calculateProgressFromCounts(3, 1);
    expect(result.percent).toBe(33);

    // 2/3 = 66.66...%
    const result2 = calculateProgressFromCounts(3, 2);
    expect(result2.percent).toBe(67);
  });
});

describe("calculateProgress", () => {
  test("counts subtasks from phases", () => {
    const phases: Phase[] = [
      {
        number: 1,
        name: "Phase 1",
        tasks: [
          {
            id: "1.1",
            title: "Task 1",
            phase: 1,
            files: [],
            depends: [],
            subtasks: [
              { text: "Done", completed: true },
              { text: "Not done", completed: false },
            ],
            flags: { parallel: false, blocked: false },
          },
        ],
      },
    ];

    const result = calculateProgress(phases);

    expect(result.total).toBe(2);
    expect(result.done).toBe(1);
    expect(result.remaining).toBe(1);
    expect(result.percent).toBe(50);
  });

  test("handles multiple phases and tasks", () => {
    const phases: Phase[] = [
      {
        number: 1,
        name: "Phase 1",
        tasks: [
          {
            id: "1.1",
            title: "Task 1",
            phase: 1,
            files: [],
            depends: [],
            subtasks: [
              { text: "Done", completed: true },
              { text: "Done", completed: true },
            ],
            flags: { parallel: false, blocked: false },
          },
        ],
      },
      {
        number: 2,
        name: "Phase 2",
        tasks: [
          {
            id: "2.1",
            title: "Task 2",
            phase: 2,
            files: [],
            depends: [],
            subtasks: [
              { text: "Not done", completed: false },
              { text: "Not done", completed: false },
            ],
            flags: { parallel: false, blocked: false },
          },
        ],
      },
    ];

    const result = calculateProgress(phases);

    expect(result.total).toBe(4);
    expect(result.done).toBe(2);
    expect(result.percent).toBe(50);
  });

  test("handles empty phases", () => {
    const result = calculateProgress([]);

    expect(result.total).toBe(0);
    expect(result.done).toBe(0);
    expect(result.percent).toBe(0);
  });

  test("handles phases with no tasks", () => {
    const phases: Phase[] = [
      {
        number: 1,
        name: "Empty Phase",
        tasks: [],
      },
    ];

    const result = calculateProgress(phases);

    expect(result.total).toBe(0);
    expect(result.done).toBe(0);
  });
});
