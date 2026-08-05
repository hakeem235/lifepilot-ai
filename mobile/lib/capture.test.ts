import { describe, expect, it } from "vitest";

import { dayDelta, describeDate, describeDraft, describeTime } from "./capture";
import type { CaptureDraft } from "./types";

const TODAY = "2026-08-05"; // a Wednesday

function draft(over: Partial<CaptureDraft> = {}): CaptureDraft {
  return {
    title: "Call the dentist",
    notes: "",
    priority: "medium",
    due_date: null,
    scheduled_date: null,
    scheduled_time: null,
    source: "ai",
    original_text: "",
    ...over,
  };
}

describe("dayDelta", () => {
  it("counts whole days in both directions", () => {
    expect(dayDelta("2026-08-06", TODAY)).toBe(1);
    expect(dayDelta("2026-08-04", TODAY)).toBe(-1);
    expect(dayDelta(TODAY, TODAY)).toBe(0);
  });

  it("crosses a month boundary", () => {
    expect(dayDelta("2026-09-01", "2026-08-31")).toBe(1);
  });

  it("is NaN for an unparseable date", () => {
    expect(dayDelta("nope", TODAY)).toBeNaN();
  });
});

describe("describeDate", () => {
  it("names the near days", () => {
    expect(describeDate(TODAY, TODAY)).toBe("Today");
    expect(describeDate("2026-08-06", TODAY)).toBe("Tomorrow");
    expect(describeDate("2026-08-04", TODAY)).toBe("Yesterday");
  });

  it("uses the weekday within the coming week", () => {
    expect(describeDate("2026-08-07", TODAY)).toBe("Friday");
  });

  it("falls back to an explicit date beyond a week", () => {
    expect(describeDate("2026-09-01", TODAY)).toMatch(/Sep/);
  });

  it("returns the raw value it cannot parse rather than inventing one", () => {
    expect(describeDate("nope", TODAY)).toBe("nope");
  });
});

describe("describeTime", () => {
  it("formats a 24-hour slot as a 12-hour clock", () => {
    expect(describeTime("14:00")).toBe("2:00 PM");
    expect(describeTime("09:30")).toBe("9:30 AM");
  });

  it("renders both noon and midnight as 12", () => {
    expect(describeTime("12:00")).toBe("12:00 PM");
    expect(describeTime("00:00")).toBe("12:00 AM");
  });
});

describe("describeDraft", () => {
  it("reads back the date and time the user described", () => {
    expect(
      describeDraft(
        draft({ due_date: "2026-08-06", scheduled_date: "2026-08-06", scheduled_time: "14:00" }),
        TODAY,
      ),
    ).toBe("Tomorrow · 2:00 PM");
  });

  it("says nothing for a bare title", () => {
    expect(describeDraft(draft(), TODAY)).toBe("");
  });

  it("mentions only high priority", () => {
    expect(describeDraft(draft({ priority: "high" }), TODAY)).toBe("High priority");
    expect(describeDraft(draft({ priority: "low" }), TODAY)).toBe("");
  });

  it("shows a date with no time", () => {
    expect(describeDraft(draft({ due_date: "2026-08-07" }), TODAY)).toBe("Friday");
  });
});
