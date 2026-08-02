/**
 * Tasks — real CRUD wired to the API. Today/Upcoming/Completed segments, priority
 * badges, a per-task progress ring, check-to-complete that persists, and a slide-up
 * add sheet. Completion toggles refetch so the list stays consistent.
 */
import type BottomSheet from "@gorhom/bottom-sheet";
import { useRef, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { AddTaskSheet } from "../../components/AddTaskSheet";
import { Badge, Fab, Fade, GlassCard, GradientBackdrop, ProgressRing } from "../../components/ui";
import { useTasks } from "../../lib/hooks";
import type { Priority } from "../../lib/types";

const SEGMENTS = ["today", "upcoming", "completed"] as const;
type Segment = (typeof SEGMENTS)[number];

export default function TasksScreen() {
  const [segment, setSegment] = useState<Segment>("today");
  const { tasks, loading, addTask, toggleComplete } = useTasks(segment);
  const sheetRef = useRef<BottomSheet>(null);

  return (
    <GradientBackdrop>
      <SafeAreaView edges={["top"]} className="flex-1">
        <View className="px-5 pt-2">
          <Text className="text-display text-text">Tasks</Text>
          {/* Segmented control */}
          <View className="mt-4 flex-row rounded-card bg-text-dim/10 p-1">
            {SEGMENTS.map((s) => (
              <Pressable
                key={s}
                onPress={() => setSegment(s)}
                className={`flex-1 items-center rounded-[16px] py-2 ${segment === s ? "bg-card" : ""}`}
              >
                <Text
                  className={`text-body capitalize ${segment === s ? "font-semibold text-text" : "text-text-dim"}`}
                >
                  {s}
                </Text>
              </Pressable>
            ))}
          </View>
        </View>

        <ScrollView
          contentContainerClassName="px-5 pb-28 pt-4"
          showsVerticalScrollIndicator={false}
        >
          {loading ? (
            <Text className="text-body text-text-dim">Loading…</Text>
          ) : tasks.length === 0 ? (
            <GlassCard>
              <Text className="text-body text-text-dim">
                {segment === "completed"
                  ? "No completed tasks yet."
                  : "Nothing here — add a task to get started."}
              </Text>
            </GlassCard>
          ) : (
            <View className="gap-3">
              {tasks.map((t) => (
                <Fade key={t.id}>
                  <GlassCard>
                    <View className="flex-row items-center gap-3">
                      <Pressable
                        accessibilityRole="checkbox"
                        accessibilityState={{ checked: t.status === "done" }}
                        onPress={() => toggleComplete(t.id, t.status !== "done")}
                        className={`h-7 w-7 items-center justify-center rounded-full border-2 ${
                          t.status === "done" ? "border-success bg-success" : "border-text-dim/40"
                        }`}
                      >
                        {t.status === "done" && (
                          <Text className="text-caption font-bold text-white">✓</Text>
                        )}
                      </Pressable>
                      <View className="flex-1">
                        <Text
                          className={`text-body ${t.status === "done" ? "text-text-dim line-through" : "text-text"}`}
                          numberOfLines={1}
                        >
                          {t.title}
                        </Text>
                        {t.due_date && (
                          <Text className="text-caption text-text-dim">Due {t.due_date}</Text>
                        )}
                      </View>
                      {t.status !== "done" && t.progress > 0 ? (
                        <ProgressRing value={t.progress} size={34} stroke={4} />
                      ) : (
                        <Badge label={t.priority} tone={t.priority as Priority} />
                      )}
                    </View>
                  </GlassCard>
                </Fade>
              ))}
            </View>
          )}
        </ScrollView>

        <Fab label="＋" accessibilityLabel="Add task" onPress={() => sheetRef.current?.expand()} />
      </SafeAreaView>

      <AddTaskSheet ref={sheetRef} onAdd={(title, priority) => addTask({ title, priority })} />
    </GradientBackdrop>
  );
}
