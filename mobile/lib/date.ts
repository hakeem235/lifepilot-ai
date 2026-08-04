/**
 * Small date helpers for the Planner (Issue 9.5). ISO dates are "YYYY-MM-DD";
 * math is done in UTC so day shifts never drift across a local timezone/DST edge.
 */

export function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Shift an ISO date by whole days (may be negative), returning a new ISO date. */
export function shiftISODate(iso: string, days: number): string {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}
