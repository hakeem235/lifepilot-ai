import { describe, expect, it } from "vitest";

import { describeCommute, formatLeaveBy, originStatus } from "./traffic";
import type { Commute } from "./types";

const LIVE: Commute = {
  available: true,
  event_title: "Client review",
  destination: "Kingdom Centre, Riyadh",
  duration_minutes: 22,
  leave_by: "2026-08-09T13:35:00Z",
  event_start: "2026-08-09T13:57:00Z",
  level: "moderate",
  distance_km: 8.4,
};

describe("formatLeaveBy", () => {
  it("renders a time for a valid timestamp", () => {
    expect(formatLeaveBy("2026-08-09T13:35:00Z")).toMatch(/\d/);
  });

  it("returns null for missing or unparseable input", () => {
    expect(formatLeaveBy(null)).toBeNull();
    expect(formatLeaveBy("not-a-date")).toBeNull();
  });
});

describe("describeCommute", () => {
  it("leads with the duration and the leave-by time", () => {
    const tile = describeCommute(LIVE, false);
    expect(tile.value).toBe("22 min");
    expect(tile.detail).toContain("Leave by");
    expect(tile.detail).toContain("Moderate traffic");
    expect(tile.live).toBe(true);
  });

  it("falls back to the event title when leave_by is unusable", () => {
    const tile = describeCommute({ ...LIVE, leave_by: null }, false);
    expect(tile.detail).toContain("Client review");
    expect(tile.live).toBe(true);
  });

  it("labels an unknown congestion level rather than implying it is clear", () => {
    const tile = describeCommute({ ...LIVE, level: "unknown" }, false);
    expect(tile.detail).toContain("Traffic unknown");
  });

  it("shows loading before an answer arrives", () => {
    const tile = describeCommute(null, true);
    expect(tile).toEqual({ value: "…", detail: "Loading", live: false });
  });

  it("distinguishes each unavailable reason instead of collapsing them", () => {
    // These call for different user reactions, so they must not read alike.
    const details = (
      [
        "no_origin",
        "calendar_not_connected",
        "no_upcoming_event_with_location",
        "lookup_failed",
        "not_configured",
        "destination_not_found",
        "origin_not_found",
        "no_route",
      ] as const
    ).map((reason) => describeCommute({ available: false, reason }, false).detail);

    expect(new Set(details).size).toBe(details.length);
    expect(details).toContain("Set your start address");
    expect(details).toContain("No trips today");
  });

  it("never claims to be live when there is no estimate", () => {
    const tile = describeCommute({ available: false, reason: "lookup_failed" }, false);
    expect(tile.live).toBe(false);
    expect(tile.value).toBe("—");
  });
});

describe("originStatus", () => {
  const base = { loading: false, saving: false, saved: false, dirty: false, origin: "" };

  it("prompts when no address is set", () => {
    expect(originStatus(base)).toBe("Set an address to enable the Traffic tile");
  });

  it("confirms the tile is using a saved address", () => {
    expect(originStatus({ ...base, origin: "Riyadh" })).toBe(
      "Traffic tile is using this address",
    );
  });

  it("reports in-flight states ahead of everything else", () => {
    expect(originStatus({ ...base, loading: true, dirty: true })).toBe("Loading…");
    expect(originStatus({ ...base, saving: true, dirty: true })).toBe("Saving…");
  });

  it("never leaves a stale 'Saved' under freshly edited text", () => {
    expect(originStatus({ ...base, saved: true, dirty: true })).toBe("Unsaved changes");
    expect(originStatus({ ...base, saved: true, dirty: false })).toBe("Saved");
  });
});
