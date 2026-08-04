/**
 * PriorityMatrix — a 2×2 Eisenhower grid (Issue 9.2) shown at the top of the
 * Planner. Groups active tasks into Do Now / Schedule / Delegate / Later with a
 * per-quadrant count and the top couple of task titles. Pure view over Task
 * fields (see lib/eisenhower.ts) — no schema change.
 */
import { Text, View } from "react-native";

import { groupByQuadrant, type Quadrant } from "../lib/eisenhower";
import type { Task } from "../lib/types";

const META: Record<Quadrant, { title: string; hint: string; dot: string }> = {
  do: { title: "Do Now", hint: "Urgent · Important", dot: "#EF4444" },
  schedule: { title: "Schedule", hint: "Important", dot: "#4F46E5" },
  delegate: { title: "Delegate", hint: "Urgent", dot: "#F59E0B" },
  later: { title: "Later", hint: "When you can", dot: "#64748B" },
};

const ORDER: Quadrant[] = ["do", "schedule", "delegate", "later"];

export function PriorityMatrix({ tasks }: { tasks: Task[] }) {
  const groups = groupByQuadrant(tasks);

  return (
    <View>
      <Text className="mb-2 text-body font-semibold text-text">Priority matrix</Text>
      <View className="flex-row flex-wrap gap-2">
        {ORDER.map((q) => {
          const items = groups[q];
          const meta = META[q];
          return (
            <View
              key={q}
              className="min-w-[46%] flex-1 rounded-card border border-border/20 bg-card p-3"
            >
              <View className="flex-row items-center justify-between">
                <View className="flex-row items-center gap-2">
                  <View
                    style={{ backgroundColor: meta.dot }}
                    className="h-2.5 w-2.5 rounded-full"
                  />
                  <Text className="text-body font-semibold text-text">{meta.title}</Text>
                </View>
                <Text className="text-caption font-semibold text-text-dim">{items.length}</Text>
              </View>
              <Text className="mt-0.5 text-caption text-text-dim">{meta.hint}</Text>
              <View className="mt-2 gap-1">
                {items.slice(0, 2).map((t) => (
                  <Text key={t.id} className="text-caption text-text" numberOfLines={1}>
                    • {t.title}
                  </Text>
                ))}
                {items.length === 0 && (
                  <Text className="text-caption text-text-dim/60">—</Text>
                )}
                {items.length > 2 && (
                  <Text className="text-caption text-text-dim">+{items.length - 2} more</Text>
                )}
              </View>
            </View>
          );
        })}
      </View>
    </View>
  );
}
