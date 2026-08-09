export type Priority = "high" | "medium" | "low";
export type TaskStatus = "open" | "done";

export interface Task {
  id: string;
  title: string;
  notes: string;
  due_date: string | null;
  scheduled_date: string | null;
  scheduled_time: string | null;
  priority: Priority;
  status: TaskStatus;
  progress: number;
  source: string;
  created_at: string;
  completed_at: string | null;
}

export interface TemplateItem {
  id: string;
  title: string;
  priority: Priority;
  order: number;
  time_offset_minutes: number;
}

export interface TaskTemplate {
  id: string;
  name: string;
  icon: string;
  items: TemplateItem[];
  is_preset: boolean;
}

export interface CalendarEvent {
  id: string;
  title: string;
  all_day: boolean;
  start: string | null;
  end: string | null;
  /** Free-text venue as typed in Google Calendar; "" for most events. */
  location: string;
}

/** Drive estimate to the next located event, or why there isn't one. */
export type Commute =
  | {
      available: true;
      event_title: string;
      destination: string;
      duration_minutes: number;
      leave_by: string | null;
      event_start: string | null;
      level: "light" | "moderate" | "heavy" | "unknown";
      distance_km: number;
    }
  | { available: false; reason: CommuteReason };

export type CommuteReason =
  | "not_configured"
  | "no_origin"
  | "calendar_not_connected"
  | "no_upcoming_event_with_location"
  | "origin_not_found"
  | "destination_not_found"
  | "lookup_failed"
  | "no_route"
  | "destination_too_far";

export interface CalendarDay {
  connected: boolean;
  events: CalendarEvent[];
  all_day: CalendarEvent[];
  error?: string;
}

export interface AppNotification {
  id: string;
  kind: "task_start" | "deadline";
  title: string;
  body: string;
  task: string | null;
  created_at: string;
  read: boolean;
}

export interface Brief {
  summary: string;
  generated_by: "ai" | "fallback";
  best_focus_window: string;
  open_tasks: number;
  due_today: number;
  high_priority: number;
}


export interface Insights {
  productivity_score: number;
  tasks_completed: number;
  focus_minutes: number;
  habit_streak: number;
  weekly_tasks: { date: string; count: number }[];
  focus_area: { date: string; minutes: number }[];
}

/** A proposed placement in a "Plan my day" preview (Issue 10.0). */
export interface PlanAssignment {
  task_id: string;
  title: string;
  priority: Priority;
  scheduled_date: string;
  scheduled_time: string;
}

/** A task that couldn't be placed — stays in the tray with a reason (D15). */
export interface PlanOverflow {
  task_id: string;
  title: string;
  priority: Priority;
  reason: string;
}

/**
 * The un-applied plan preview. Holding this client-side is deliberate: it is a
 * proposal, not state — nothing exists server-side until the user confirms and
 * the app posts the accepted subset back to the apply endpoint (D10).
 */
export interface PlanProposal {
  kind: "plan_day";
  date: string;
  generated_by: "ai" | "fallback";
  generated_at: string;
  calendar_connected: boolean;
  free_hours: number[];
  assignments: PlanAssignment[];
  overflow: PlanOverflow[];
  events: { title: string; start: string | null; end: string | null }[];
}

export interface PlanApplyResult {
  applied: { task_id: string; title: string; scheduled_date: string; scheduled_time: string }[];
  rejected: { task_id: string | null; reason: string }[];
  previous: { task_id: string; scheduled_date: string | null; scheduled_time: string | null }[];
}

/** A task drafted from free text, pending the user's confirmation (Issue 10.1). */
export interface CaptureDraft {
  title: string;
  notes: string;
  priority: Priority;
  due_date: string | null;
  scheduled_date: string | null;
  scheduled_time: string | null;
  source: string;
  original_text: string;
}

export interface CaptureProposal {
  kind: "capture";
  generated_by: "ai" | "fallback";
  draft: CaptureDraft | null;
  understood: boolean;
  slot_conflict: boolean;
}

/** The evening review (Issue 10.2) — a summary plus proposed roll-forwards. */
export interface DailyReview {
  kind: "daily_review";
  date: string;
  reschedule_date: string;
  generated_by: "ai" | "fallback";
  summary: string;
  done: { task_id: string; title: string }[];
  slipped: { task_id: string; title: string; priority: Priority }[];
  completion_rate: number;
  proposed_moves: PlanAssignment[];
  overflow: { task_id: string; title: string; reason: string }[];
  calendar_connected: boolean;
  free_hours: number[];
}

/** Prior slot of a task an apply moved — the payload that makes it reversible. */
export interface PreviousPlacement {
  task_id: string;
  scheduled_date: string | null;
  scheduled_time: string | null;
}

export interface UndoResult {
  restored: string[];
  deleted: string[];
  rejected: { task_id: string | null; reason: string }[];
}

export interface Note {
  id: string;
  title: string;
  body: string;
  /** Server-derived: the real title, else the body's first line. */
  display_title: string;
  pinned: boolean;
  source: "manual" | "ai";
  created_at: string;
  updated_at: string;
}
