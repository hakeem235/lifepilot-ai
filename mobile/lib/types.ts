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
}

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

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
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
