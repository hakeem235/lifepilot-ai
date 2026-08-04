/**
 * Planner — drag-drop daily timeline (Issue 9.0).
 *
 * An hour-by-hour timeline (7 AM–9 PM) plus an "Unscheduled" tray of tasks with
 * no scheduled_date. Long-press a chip to lift it, drag it onto an hour slot to
 * schedule (or between slots to reschedule), or back onto the tray to unschedule.
 * Every drop PATCHes scheduled_date/scheduled_time and refetches, so it persists
 * across reload.
 *
 * DnD is native (D7): Reanimated + gesture-handler, no web DnD lib. The dragged
 * chip is drawn as a single absolute "ghost" overlay at the screen root so it is
 * never clipped while crossing between the tray and timeline scroll containers.
 */
import { useCallback, useRef, useState } from "react";
import { ScrollView, Text, View, type View as RNView } from "react-native";
import { Gesture, GestureDetector } from "react-native-gesture-handler";
import Animated, {
  runOnJS,
  type SharedValue,
  useAnimatedStyle,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";
import { SafeAreaView } from "react-native-safe-area-context";

import { Badge, GlassCard, GradientBackdrop } from "../../components/ui";
import { usePlanner } from "../../lib/hooks";
import type { Priority, Task } from "../../lib/types";

const HOURS = Array.from({ length: 15 }, (_, i) => i + 7); // 7 AM … 9 PM
const SLOT_H = 64;

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function hourLabel(h: number): string {
  const ampm = h < 12 ? "AM" : "PM";
  const display = h % 12 === 0 ? 12 : h % 12;
  return `${display} ${ampm}`;
}

function ChipVisual({ task }: { task: Task }) {
  return (
    <View className="flex-row items-center gap-2 rounded-chip bg-card px-3 py-2 shadow-sm">
      <Text className="max-w-[160px] text-body text-text" numberOfLines={1}>
        {task.title}
      </Text>
      <Badge label={task.priority} tone={task.priority as Priority} />
    </View>
  );
}

type DragCtx = {
  ghostX: SharedValue<number>;
  ghostY: SharedValue<number>;
  baseX: SharedValue<number>;
  baseY: SharedValue<number>;
  onBegin: (task: Task, ref: RNView | null) => void;
  onEnd: (absX: number, absY: number) => void;
};

/**
 * A draggable task chip. Hoisted to module scope (not defined inside the screen)
 * so a re-render from the drag-start state update reconciles it in place instead
 * of remounting the GestureDetector mid-gesture. The lifted original is dimmed via
 * a local shared value, so no React re-render is needed to show the "picked up" state.
 */
function DraggableChip({ task, ctx }: { task: Task; ctx: DragCtx }) {
  const ref = useRef<RNView>(null);
  const dim = useSharedValue(1);

  const pan = Gesture.Pan()
    .activateAfterLongPress(160)
    .onStart(() => {
      dim.value = 0.3;
      runOnJS(ctx.onBegin)(task, ref.current);
    })
    .onUpdate((e) => {
      ctx.ghostX.value = ctx.baseX.value + e.translationX;
      ctx.ghostY.value = ctx.baseY.value + e.translationY;
    })
    .onEnd((e) => {
      runOnJS(ctx.onEnd)(e.absoluteX, e.absoluteY);
    })
    .onFinalize(() => {
      dim.value = 1;
    });

  const style = useAnimatedStyle(() => ({ opacity: dim.value }));

  return (
    <GestureDetector gesture={pan}>
      <Animated.View ref={ref} collapsable={false} style={style}>
        <ChipVisual task={task} />
      </Animated.View>
    </GestureDetector>
  );
}

export default function PlannerScreen() {
  const dateISO = todayISO();
  const { scheduled, unscheduled, loading, schedule } = usePlanner(dateISO);

  // Ghost overlay shared values — the single element that follows the finger.
  const ghostX = useSharedValue(0);
  const ghostY = useSharedValue(0);
  const baseX = useSharedValue(0);
  const baseY = useSharedValue(0);
  const ghostVisible = useSharedValue(0);
  const [dragTask, setDragTask] = useState<Task | null>(null);
  const activeIdRef = useRef<string | null>(null);

  // Layout refs measured on-demand (fresh measure accounts for current scroll).
  const trayRef = useRef<RNView>(null);
  const timelineRef = useRef<RNView>(null);

  const beginDrag = useCallback(
    (task: Task, ref: RNView | null) => {
      if (!ref) return;
      ref.measureInWindow((x, y) => {
        baseX.value = x;
        baseY.value = y;
        ghostX.value = x;
        ghostY.value = y;
        ghostVisible.value = 1;
        activeIdRef.current = task.id;
        setDragTask(task);
      });
    },
    [baseX, baseY, ghostX, ghostY, ghostVisible],
  );

  const endDrag = useCallback(
    (absX: number, absY: number) => {
      const id = activeIdRef.current;
      activeIdRef.current = null;
      ghostVisible.value = withTiming(0, { duration: 120 });
      setDragTask(null);
      if (!id) return;

      trayRef.current?.measureInWindow((tx, ty, tw, th) => {
        if (absY >= ty && absY <= ty + th && absX >= tx && absX <= tx + tw) {
          void schedule(id, null, null); // dropped on tray → unschedule
          return;
        }
        timelineRef.current?.measureInWindow((cx, cy, cw, ch) => {
          const rel = absY - cy;
          if (rel < 0 || rel > ch) return; // dropped nowhere useful → snap back
          const idx = Math.min(HOURS.length - 1, Math.max(0, Math.floor(rel / SLOT_H)));
          const hour = HOURS[idx];
          void schedule(id, dateISO, `${String(hour).padStart(2, "0")}:00`);
        });
      });
    },
    [dateISO, ghostVisible, schedule],
  );

  const ghostStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: ghostX.value }, { translateY: ghostY.value }],
    opacity: ghostVisible.value,
  }));

  const ctx: DragCtx = { ghostX, ghostY, baseX, baseY, onBegin: beginDrag, onEnd: endDrag };

  const bySlot = (hour: number) =>
    scheduled.filter((t) => (t.scheduled_time ?? "").startsWith(String(hour).padStart(2, "0") + ":"));

  return (
    <GradientBackdrop>
      <SafeAreaView edges={["top"]} className="flex-1">
        <View className="px-5 pt-2">
          <Text className="text-display text-text">Planner</Text>
          <Text className="mt-1 text-body text-text-dim">
            {new Date(dateISO).toLocaleDateString(undefined, {
              weekday: "long",
              month: "long",
              day: "numeric",
            })}
          </Text>
        </View>

        {/* Unscheduled tray */}
        <View ref={trayRef} collapsable={false} className="mt-3 px-5">
          <Text className="mb-2 text-caption font-semibold uppercase text-text-dim">
            Unscheduled
          </Text>
          {unscheduled.length === 0 ? (
            <GlassCard>
              <Text className="text-caption text-text-dim">
                Nothing waiting — every task has a home.
              </Text>
            </GlassCard>
          ) : (
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerClassName="gap-2 pr-5"
            >
              {unscheduled.map((t) => (
                <DraggableChip key={t.id} task={t} ctx={ctx} />
              ))}
            </ScrollView>
          )}
        </View>

        {/* Timeline */}
        <ScrollView
          className="mt-4 flex-1"
          contentContainerClassName="px-5 pb-28"
          showsVerticalScrollIndicator={false}
        >
          <View ref={timelineRef} collapsable={false}>
            {HOURS.map((h) => (
              <View
                key={h}
                style={{ height: SLOT_H }}
                className="flex-row border-t border-text-dim/10"
              >
                <Text className="w-16 pt-1 text-caption text-text-dim">{hourLabel(h)}</Text>
                <View className="flex-1 gap-1 py-1">
                  {bySlot(h).map((t) => (
                    <DraggableChip key={t.id} task={t} ctx={ctx} />
                  ))}
                </View>
              </View>
            ))}
          </View>
          {loading && <Text className="mt-4 text-caption text-text-dim">Syncing…</Text>}
        </ScrollView>
      </SafeAreaView>

      {/* Drag ghost — screen-root overlay, never clipped by a scroll container */}
      {dragTask && (
        <Animated.View
          pointerEvents="none"
          style={[{ position: "absolute", top: 0, left: 0, zIndex: 1000 }, ghostStyle]}
        >
          <ChipVisual task={dragTask} />
        </Animated.View>
      )}
    </GradientBackdrop>
  );
}
