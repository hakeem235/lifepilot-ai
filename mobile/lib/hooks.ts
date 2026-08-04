/**
 * Data hooks over the DRF API. Lightweight (no react-query dep): each hook owns
 * fetch + loading/error state and exposes imperative mutators that refetch.
 * All calls carry the Clerk JWT via useApi().
 */
import { useCallback, useEffect, useState } from "react";

import { useApi } from "./api";
import type { Brief, ChatMessage, Insights, Priority, Task } from "./types";

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
