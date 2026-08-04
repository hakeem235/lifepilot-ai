import { describe, expect, it } from "vitest";

import { groupByQuadrant, isUrgent, quadrantOf } from "./eisenhower";
import type { Priority, Task } from "./types";

const TODAY = new Date("2026-08-04T12:00:00Z");

function task(overrides: Partial<Task>): Task {
  return {
    id: Math.random().toString(36).slice(2),
    title: "t",
    notes: "",
    due_date: null,
    scheduled_date: null,
    scheduled_time: null,
    priority: "medium" as Priority,
    status: "open",
    progress: 0,
    source: "manual",
    created_at: "2026-08-01T00:00:00Z",
    completed_at: null,
    ...overrides,
  };
}

describe("quadrantOf", () => {
  it("urgent + important → do", () => {
    expect(quadrantOf(task({ priority: "high", due_date: "2026-08-04" }), TODAY)).toBe("do");
  });

  it("overdue + important → do", () => {
    expect(quadrantOf(task({ priority: "high", due_date: "2026-08-01" }), TODAY)).toBe("do");
  });

  it("important, no due date → schedule", () => {
    expect(quadrantOf(task({ priority: "high", due_date: null }), TODAY)).toBe("schedule");
  });

  it("important, future due date → schedule", () => {
    expect(quadrantOf(task({ priority: "high", due_date: "2026-08-10" }), TODAY)).toBe("schedule");
  });

  it("urgent, not important → delegate", () => {
    expect(quadrantOf(task({ priority: "low", due_date: "2026-08-04" }), TODAY)).toBe("delegate");
  });

  it("neither → later", () => {
    expect(quadrantOf(task({ priority: "medium", due_date: null }), TODAY)).toBe("later");
  });
});

describe("isUrgent", () => {
  it("is false without a due date", () => {
    expect(isUrgent(task({ due_date: null }), TODAY)).toBe(false);
  });

  it("is true on the due day and while overdue", () => {
    expect(isUrgent(task({ due_date: "2026-08-04" }), TODAY)).toBe(true);
    expect(isUrgent(task({ due_date: "2026-07-30" }), TODAY)).toBe(true);
  });

  it("is false for a future due date", () => {
    expect(isUrgent(task({ due_date: "2026-08-05" }), TODAY)).toBe(false);
  });
});

describe("groupByQuadrant", () => {
  it("buckets open tasks and drops completed ones", () => {
    const groups = groupByQuadrant(
      [
        task({ priority: "high", due_date: "2026-08-04" }), // do
        task({ priority: "high" }), // schedule
        task({ priority: "low", due_date: "2026-08-04" }), // delegate
        task({ priority: "medium" }), // later
        task({ priority: "high", due_date: "2026-08-04", status: "done" }), // excluded
      ],
      TODAY,
    );
    expect(groups.do).toHaveLength(1);
    expect(groups.schedule).toHaveLength(1);
    expect(groups.delegate).toHaveLength(1);
    expect(groups.later).toHaveLength(1);
  });
});
