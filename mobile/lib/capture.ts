/**
 * Presentation logic for the capture preview (Issue 10.1).
 *
 * The user is confirming a task they described in words, so the preview has to
 * read back in words — "Tomorrow · 2:00 PM" tells them the date was understood
 * correctly, where "2026-08-06" makes them do the arithmetic the feature was
 * supposed to save them. Pure and separately tested, because a wrong label here
 * means the user confirms a date they didn't mean.
 */
import type { CaptureDraft } from "./types";

/** Whole days from `today` to `iso`, both plain YYYY-MM-DD dates. */
export function dayDelta(iso: string, today: string): number {
  const a = Date.parse(`${iso}T00:00:00Z`);
  const b = Date.parse(`${today}T00:00:00Z`);
  if (Number.isNaN(a) || Number.isNaN(b)) return NaN;
  return Math.round((a - b) / 86_400_000);
}

/** "Today" / "Tomorrow" / a weekday within the week / an explicit date beyond. */
export function describeDate(iso: string, today: string): string {
  const delta = dayDelta(iso, today);
  if (Number.isNaN(delta)) return iso;
  if (delta === 0) return "Today";
  if (delta === 1) return "Tomorrow";
  if (delta === -1) return "Yesterday";
  const date = new Date(`${iso}T00:00:00Z`);
  if (delta > 1 && delta < 7) {
    return date.toLocaleDateString(undefined, { weekday: "long", timeZone: "UTC" });
  }
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", timeZone: "UTC" });
}

/** "14:00" → "2:00 PM". */
export function describeTime(time: string): string {
  const [rawHour, rawMinute = "00"] = time.split(":");
  const hour = Number(rawHour);
  if (Number.isNaN(hour)) return time;
  const ampm = hour < 12 ? "AM" : "PM";
  const display = hour % 12 === 0 ? 12 : hour % 12;
  return `${display}:${rawMinute.padStart(2, "0")} ${ampm}`;
}

/**
 * The one-line summary under the title. Empty when the draft is just a title —
 * there is nothing to reassure the user about, so we say nothing.
 */
export function describeDraft(draft: CaptureDraft, today: string): string {
  const parts: string[] = [];
  if (draft.due_date) parts.push(describeDate(draft.due_date, today));
  if (draft.scheduled_time) parts.push(describeTime(draft.scheduled_time));
  if (draft.priority === "high") parts.push("High priority");
  return parts.join(" · ");
}
