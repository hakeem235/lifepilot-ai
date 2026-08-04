import { describe, expect, it } from "vitest";

import { shiftISODate } from "./date";

describe("shiftISODate", () => {
  it("advances by whole days", () => {
    expect(shiftISODate("2026-08-04", 1)).toBe("2026-08-05");
    expect(shiftISODate("2026-08-04", 3)).toBe("2026-08-07");
  });

  it("goes backwards", () => {
    expect(shiftISODate("2026-08-04", -1)).toBe("2026-08-03");
  });

  it("crosses month boundaries", () => {
    expect(shiftISODate("2026-08-31", 1)).toBe("2026-09-01");
    expect(shiftISODate("2026-03-01", -1)).toBe("2026-02-28");
  });

  it("crosses year boundaries", () => {
    expect(shiftISODate("2026-12-31", 1)).toBe("2027-01-01");
  });

  it("is a no-op for zero", () => {
    expect(shiftISODate("2026-08-04", 0)).toBe("2026-08-04");
  });
});
