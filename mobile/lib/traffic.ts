/**
 * Presentation logic for the commute tile.
 *
 * The estimate itself is computed server-side (the Mapbox token must never
 * reach the bundle). This file only decides what the tile says — including
 * what it says when there is no estimate, which is the common case.
 */
import type { Commute, CommuteReason } from "./types";

export type CommuteTile = {
  value: string;
  detail: string;
  /** True when we are showing a real measured estimate. */
  live: boolean;
};

/**
 * Why there is no estimate, in the user's terms.
 *
 * Each reason is actionable or clearly not the user's fault. We never collapse
 * these into a generic "unavailable" — "set your home address" and "Mapbox is
 * down" call for completely different reactions.
 */
const REASONS: Record<CommuteReason, string> = {
  not_configured: "Not set up yet",
  no_origin: "Set your start address",
  calendar_not_connected: "Connect your calendar",
  no_upcoming_event_with_location: "No trips today",
  origin_not_found: "Start address not found",
  destination_not_found: "Venue not on the map",
  lookup_failed: "Traffic unavailable",
  no_route: "No driving route",
};

const LEVEL_LABEL: Record<string, string> = {
  light: "Light traffic",
  moderate: "Moderate traffic",
  heavy: "Heavy traffic",
  unknown: "Traffic unknown",
};

/** "13:35" in the device's locale, or null if the timestamp is unusable. */
export function formatLeaveBy(iso: string | null): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
}

export function describeCommute(
  commute: Commute | null,
  loading: boolean,
): CommuteTile {
  if (loading) return { value: "…", detail: "Loading", live: false };
  if (!commute) return { value: "—", detail: "Unavailable", live: false };

  if (!commute.available) {
    return { value: "—", detail: REASONS[commute.reason] ?? "Unavailable", live: false };
  }

  const leaveBy = formatLeaveBy(commute.leave_by);
  const level = LEVEL_LABEL[commute.level] ?? LEVEL_LABEL.unknown;
  return {
    value: `${commute.duration_minutes} min`,
    // "Leave by" is the actionable half; fall back to the destination when the
    // event start was unusable, so the tile still says where it is measuring to.
    detail: leaveBy ? `Leave by ${leaveBy} · ${level}` : `${commute.event_title} · ${level}`,
    live: true,
  };
}
