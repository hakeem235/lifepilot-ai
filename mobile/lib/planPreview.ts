/**
 * Pure logic behind the "Plan my day" preview sheet (Issue 10.0).
 *
 * Kept out of the component so the rules the user is confirming against are
 * unit-testable: which placements survive their edits, and where a placement can
 * move to. The server re-validates all of it anyway (D10) — this is what makes
 * the preview behave predictably before it gets there.
 */
import type { PlanAssignment } from "./types";

export type Dropped = Record<string, boolean>;
export type Moved = Record<string, string>;

export function hourOf(time: string): number {
  return Number(time.slice(0, 2));
}

export function toTime(hour: number): string {
  return `${String(hour).padStart(2, "0")}:00`;
}

/** The placements the user is actually confirming: not dropped, with edits applied. */
export function keptAssignments(
  assignments: PlanAssignment[],
  dropped: Dropped,
  moved: Moved,
): PlanAssignment[] {
  return assignments
    .filter((a) => !dropped[a.task_id])
    .map((a) => ({ ...a, scheduled_time: moved[a.task_id] ?? a.scheduled_time }));
}

/**
 * Free hours a placement may move to: the ones no other kept placement holds,
 * plus its own current hour. Keeps the preview from proposing a double-book
 * before the request even leaves the device (D15).
 */
export function moveOptions(
  freeHours: number[],
  kept: PlanAssignment[],
  taskId: string,
  currentHour: number,
): number[] {
  const taken = new Set(
    kept.filter((a) => a.task_id !== taskId).map((a) => hourOf(a.scheduled_time)),
  );
  return freeHours.filter((h) => h === currentHour || !taken.has(h)).sort((a, b) => a - b);
}

/**
 * The hour a placement lands on when nudged earlier (-1) or later (+1).
 * Returns null at either end, so the caller simply does nothing.
 */
export function shiftedHour(
  freeHours: number[],
  kept: PlanAssignment[],
  taskId: string,
  currentHour: number,
  direction: 1 | -1,
): number | null {
  const options = moveOptions(freeHours, kept, taskId, currentHour);
  const next = options[options.indexOf(currentHour) + direction];
  return next ?? null;
}
