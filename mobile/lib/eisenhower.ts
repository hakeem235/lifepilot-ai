/**
 * Eisenhower matrix classification (Issue 9.2).
 *
 * Pure, client-side derivation from existing Task fields — no schema change:
 *   important = priority is "high"
 *   urgent    = has a due_date that is today or overdue
 *
 * Quadrants:
 *   do       urgent + important      → "Do Now"
 *   schedule important, not urgent   → "Schedule"
 *   delegate urgent, not important   → "Delegate"
 *   later    neither                 → "Later"
 */
import type { Task } from "./types";

export type Quadrant = "do" | "schedule" | "delegate" | "later";

export const QUADRANTS: Quadrant[] = ["do", "schedule", "delegate", "later"];

function toISODate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

export function isImportant(task: Task): boolean {
  return task.priority === "high";
}

export function isUrgent(task: Task, today: Date = new Date()): boolean {
  if (!task.due_date) return false;
  // due_date is a YYYY-MM-DD string, so lexical compare is a valid date compare.
  return task.due_date <= toISODate(today);
}

export function quadrantOf(task: Task, today: Date = new Date()): Quadrant {
  const important = isImportant(task);
  const urgent = isUrgent(task, today);
  if (urgent && important) return "do";
  if (!urgent && important) return "schedule";
  if (urgent && !important) return "delegate";
  return "later";
}

/** Group active (open) tasks into the four quadrants. Done tasks are excluded. */
export function groupByQuadrant(
  tasks: Task[],
  today: Date = new Date(),
): Record<Quadrant, Task[]> {
  const groups: Record<Quadrant, Task[]> = { do: [], schedule: [], delegate: [], later: [] };
  for (const task of tasks) {
    if (task.status !== "open") continue;
    groups[quadrantOf(task, today)].push(task);
  }
  return groups;
}
