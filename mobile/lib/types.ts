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
