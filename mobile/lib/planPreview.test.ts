import { describe, expect, it } from "vitest";

import { keptAssignments, moveOptions, shiftedHour, toTime } from "./planPreview";
import type { PlanAssignment } from "./types";

function assignment(task_id: string, time: string): PlanAssignment {
  return {
    task_id,
    title: task_id,
    priority: "medium",
    scheduled_date: "2026-08-05",
    scheduled_time: time,
  };
}

const FREE = [7, 8, 9, 10];

describe("keptAssignments", () => {
  const plan = [assignment("a", "07:00"), assignment("b", "08:00")];

  it("keeps everything when the user edits nothing", () => {
    expect(keptAssignments(plan, {}, {})).toEqual(plan);
  });

  it("drops the placements the user skipped", () => {
    expect(keptAssignments(plan, { a: true }, {}).map((x) => x.task_id)).toEqual(["b"]);
  });

  it("applies the user's moves", () => {
    const [first] = keptAssignments(plan, {}, { a: "10:00" });
    expect(first.scheduled_time).toBe("10:00");
  });

  it("ignores a move for a task that was dropped", () => {
    expect(keptAssignments(plan, { a: true }, { a: "10:00" })).toHaveLength(1);
  });
});

describe("moveOptions", () => {
  it("excludes hours held by other kept placements", () => {
    const kept = [assignment("a", "07:00"), assignment("b", "09:00")];
    expect(moveOptions(FREE, kept, "a", 7)).toEqual([7, 8, 10]);
  });

  it("always includes the placement's own current hour", () => {
    const kept = [assignment("a", "07:00")];
    expect(moveOptions(FREE, kept, "a", 7)).toContain(7);
  });
});

describe("shiftedHour", () => {
  const kept = [assignment("a", "08:00"), assignment("b", "09:00")];

  it("moves later, skipping an hour another task holds", () => {
    // 9 is taken by b, so a jumps from 8 straight to 10.
    expect(shiftedHour(FREE, kept, "a", 8, 1)).toBe(10);
  });

  it("moves earlier", () => {
    expect(shiftedHour(FREE, kept, "a", 8, -1)).toBe(7);
  });

  it("returns null at the start of the day", () => {
    expect(shiftedHour(FREE, kept, "a", 7, -1)).toBeNull();
  });

  it("returns null at the end of the day", () => {
    expect(shiftedHour(FREE, kept, "a", 10, 1)).toBeNull();
  });
});

describe("toTime", () => {
  it("pads to an HH:MM slot the API accepts", () => {
    expect(toTime(9)).toBe("09:00");
    expect(toTime(14)).toBe("14:00");
  });
});
