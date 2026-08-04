/**
 * Data hooks over the DRF API. Lightweight (no react-query dep): each hook owns
 * fetch + loading/error state and exposes imperative mutators that refetch.
 * All calls carry the Clerk JWT via useApi().
 */
import { useCallback, useEffect, useState } from "react";

import { useApi } from "./api";
import * as WebBrowser from "expo-web-browser";

import { getPushToken, pushPlatform } from "./notifications";
import type {
  AppNotification,
  Brief,
  CalendarDay,
  ChatMessage,
  Insights,
  Priority,
  Task,
  TaskTemplate,
} from "./types";

type Segment = "today" | "upcoming" | "completed";

export function useTasks(segment?: Segment) {
  const api = useApi();
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const q = segment ? `?segment=${segment}` : "";
      const res = await api(`/api/tasks/${q}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setTasks(await res.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load tasks");
    } finally {
      setLoading(false);
    }
  }, [api, segment]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const addTask = useCallback(
    async (input: { title: string; priority?: Priority; due_date?: string | null }) => {
      const res = await api("/api/tasks/", { method: "POST", body: JSON.stringify(input) });
      await refresh();
      return res.ok;
    },
    [api, refresh],
  );

  const toggleComplete = useCallback(
    async (id: string, done: boolean) => {
      await api(`/api/tasks/${id}/complete/`, {
        method: "POST",
        body: JSON.stringify({ done }),
      });
      await refresh();
    },
    [api, refresh],
  );

  return { tasks, loading, error, refresh, addTask, toggleComplete };
}

/**
 * Planner data for a single day: the timeline (tasks scheduled on `dateISO`) plus
 * the unscheduled tray. `schedule` PATCHes a task's scheduled_date/time — pass
 * nulls to send it back to the tray — then refetches both lists so the drop
 * persists and survives reload (the 9.0 acceptance path).
 */
export function usePlanner(dateISO: string) {
  const api = useApi();
  const [scheduled, setScheduled] = useState<Task[]>([]);
  const [unscheduled, setUnscheduled] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [dayRes, trayRes] = await Promise.all([
        api(`/api/tasks/?scheduled_date=${dateISO}`),
        api(`/api/tasks/?unscheduled=true`),
      ]);
      if (dayRes.ok) setScheduled(await dayRes.json());
      if (trayRes.ok) setUnscheduled(await trayRes.json());
    } finally {
      setLoading(false);
    }
  }, [api, dateISO]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const schedule = useCallback(
    async (id: string, date: string | null, time: string | null) => {
      // Optimistic move so the chip lands under the finger instantly; refresh reconciles.
      const apply = (t: Task): Task => ({ ...t, scheduled_date: date, scheduled_time: time });
      setScheduled((prev) => {
        const found = prev.find((t) => t.id === id);
        const rest = prev.filter((t) => t.id !== id);
        const fromTray = unscheduled.find((t) => t.id === id);
        const moved = found ?? fromTray;
        return date ? [...rest, ...(moved ? [apply(moved)] : [])] : rest;
      });
      setUnscheduled((prev) => {
        const found = prev.find((t) => t.id === id);
        const rest = prev.filter((t) => t.id !== id);
        const fromDay = scheduled.find((t) => t.id === id);
        const moved = found ?? fromDay;
        return date ? rest : [...rest, ...(moved ? [apply(moved)] : [])];
      });
      await api(`/api/tasks/${id}/`, {
        method: "PATCH",
        body: JSON.stringify({ scheduled_date: date, scheduled_time: time }),
      });
      await refresh();
    },
    [api, refresh, scheduled, unscheduled],
  );

  return { scheduled, unscheduled, loading, refresh, schedule };
}

/**
 * Task templates / routines (Issue 9.1): lists system presets + the user's own
 * templates, and applies one onto a chosen day (creates the tasks server-side).
 */
export function useTemplates() {
  const api = useApi();
  const [templates, setTemplates] = useState<TaskTemplate[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await api("/api/templates/");
        if (alive && res.ok) setTemplates(await res.json());
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [api]);

  const apply = useCallback(
    async (id: string, dateISO: string): Promise<boolean> => {
      const res = await api(`/api/templates/${id}/apply/`, {
        method: "POST",
        body: JSON.stringify({ date: dateISO }),
      });
      return res.ok;
    },
    [api],
  );

  return { templates, loading, apply };
}

/**
 * Google Calendar read-only overlay (Issue 9.3). Fetches a day's events; when
 * not connected, `connect()` opens the server-issued consent URL in a browser
 * (server-side OAuth — no client-side calendar credentials) and refreshes on
 * return. Degrades cleanly: with no server config, `connected` stays false.
 */
export function useCalendar(dateISO: string) {
  const api = useApi();
  const [day, setDay] = useState<CalendarDay>({
    connected: false,
    events: [],
    all_day: [],
  });

  const refresh = useCallback(async () => {
    try {
      const res = await api(`/api/gcal/events/?date=${dateISO}`);
      if (res.ok) setDay(await res.json());
    } catch {
      // Leave the last-known (or empty) state; the overlay is non-critical.
    }
  }, [api, dateISO]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const connect = useCallback(async (): Promise<boolean> => {
    const res = await api("/api/gcal/auth-url/");
    if (!res.ok) return false;
    const { url } = await res.json();
    await WebBrowser.openAuthSessionAsync(url, "lifepilot://planner");
    await refresh();
    return true;
  }, [api, refresh]);

  return { day, refresh, connect };
}

/**
 * Notifications (Issue 9.4): registers this device's Expo push token on mount,
 * then exposes the in-app center (list + unread count) with mark-read helpers.
 */
export function useNotifications() {
  const api = useApi();
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [unread, setUnread] = useState(0);

  const refresh = useCallback(async () => {
    try {
      const res = await api("/api/notifications/");
      if (res.ok) {
        const data = await res.json();
        setNotifications(data.notifications);
        setUnread(data.unread);
      }
    } catch {
      // non-critical surface
    }
  }, [api]);

  useEffect(() => {
    let alive = true;
    (async () => {
      const token = await getPushToken();
      if (token && alive) {
        await api("/api/notifications/register/", {
          method: "POST",
          body: JSON.stringify({ token, platform: pushPlatform }),
        });
      }
      if (alive) await refresh();
    })();
    return () => {
      alive = false;
    };
  }, [api, refresh]);

  const markRead = useCallback(
    async (id: string) => {
      await api(`/api/notifications/${id}/read/`, { method: "POST" });
      await refresh();
    },
    [api, refresh],
  );

  const markAllRead = useCallback(async () => {
    await api("/api/notifications/read-all/", { method: "POST" });
    await refresh();
  }, [api, refresh]);

  return { notifications, unread, refresh, markRead, markAllRead };
}

export function useBrief() {
  const api = useApi();
  const [brief, setBrief] = useState<Brief | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await api("/api/ai/brief/");
        if (alive && res.ok) setBrief(await res.json());
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [api]);

  return { brief, loading };
}

export function useChat() {
  const api = useApi();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      const res = await api("/api/ai/chat/");
      if (alive && res.ok) setMessages(await res.json());
    })();
    return () => {
      alive = false;
    };
  }, [api]);

  const send = useCallback(
    async (message: string) => {
      setMessages((m) => [...m, { role: "user", content: message }]);
      setSending(true);
      try {
        const res = await api("/api/ai/chat/", {
          method: "POST",
          body: JSON.stringify({ message }),
        });
        const data = await res.json();
        setMessages((m) => [...m, { role: "assistant", content: data.reply }]);
      } catch {
        setMessages((m) => [
          ...m,
          { role: "assistant", content: "I couldn't reach the server. Try again." },
        ]);
      } finally {
        setSending(false);
      }
    },
    [api],
  );

  return { messages, sending, send };
}

export function useInsights() {
  const api = useApi();
  const [insights, setInsights] = useState<Insights | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const res = await api("/api/insights/");
        if (alive && res.ok) setInsights(await res.json());
      } finally {
        if (alive) setLoading(false);
      }
    })();
    return () => {
      alive = false;
    };
  }, [api]);

  return { insights, loading };
}
