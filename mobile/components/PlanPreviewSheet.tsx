/**
 * PlanPreviewSheet — the confirm gate for "Plan my day" (Issue 10.0, D10).
 *
 * Nothing the AI proposes reaches the user's timeline until they act here. The
 * user can accept the whole plan, drop individual placements, move one to another
 * free hour, or reject the lot. Only the kept placements are sent to the apply
 * endpoint — which re-validates them server-side before writing.
 *
 * Overflow tasks are shown, not hidden: they stay in the tray with the reason the
 * planner gave (D15).
 */
import BottomSheet, { BottomSheetBackdrop, BottomSheetScrollView } from "@gorhom/bottom-sheet";
import { forwardRef, useCallback, useMemo, useState } from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";

import { Badge } from "./ui";
import { hourOf, keptAssignments, shiftedHour, toTime } from "../lib/planPreview";
import type { PlanAssignment, PlanProposal } from "../lib/types";
import { useTheme } from "../theme/ThemeProvider";

function hourLabel(time: string): string {
  const hour = hourOf(time);
  const ampm = hour < 12 ? "AM" : "PM";
  const display = hour % 12 === 0 ? 12 : hour % 12;
  return `${display} ${ampm}`;
}

export const PlanPreviewSheet = forwardRef<
  BottomSheet,
  {
    proposal: PlanProposal | null;
    applying: boolean;
    onConfirm: (assignments: PlanAssignment[]) => void;
    onReject: () => void;
  }
>(function PlanPreviewSheet({ proposal, applying, onConfirm, onReject }, ref) {
  const { colors } = useTheme();
  // Local edits to the proposal. Keyed by task_id so a re-proposal starts clean.
  const [dropped, setDropped] = useState<Record<string, boolean>>({});
  const [moved, setMoved] = useState<Record<string, string>>({});

  const renderBackdrop = useCallback(
    (props: React.ComponentProps<typeof BottomSheetBackdrop>) => (
      <BottomSheetBackdrop {...props} disappearsOnIndex={-1} appearsOnIndex={0} />
    ),
    [],
  );

  const kept = useMemo<PlanAssignment[]>(
    () => (proposal ? keptAssignments(proposal.assignments, dropped, moved) : []),
    [proposal, dropped, moved],
  );

  if (proposal === null) return null;

  /** Move a placement to the next free hour that no other kept placement holds. */
  const shift = (assignment: PlanAssignment, direction: 1 | -1) => {
    const current = hourOf(moved[assignment.task_id] ?? assignment.scheduled_time);
    const next = shiftedHour(proposal.free_hours, kept, assignment.task_id, current, direction);
    if (next !== null) {
      setMoved((prev) => ({ ...prev, [assignment.task_id]: toTime(next) }));
    }
  };

  const reset = () => {
    setDropped({});
    setMoved({});
  };

  return (
    <BottomSheet
      ref={ref}
      index={-1}
      snapPoints={["75%"]}
      enablePanDownToClose
      onClose={reset}
      backdropComponent={renderBackdrop}
      backgroundStyle={{ backgroundColor: colors.card }}
      handleIndicatorStyle={{ backgroundColor: colors.textDim }}
    >
      <BottomSheetScrollView contentContainerStyle={{ padding: 20, gap: 12 }}>
        <View className="flex-row items-center justify-between">
          <Text className="text-title text-text">Your proposed day</Text>
          {proposal.generated_by === "fallback" && (
            <Badge label="offline plan" tone="low" />
          )}
        </View>
        <Text className="text-caption text-text-dim">
          Nothing is scheduled until you tap Apply. Drop anything you don&apos;t want, or
          move it to another free hour.
        </Text>

        {!proposal.calendar_connected && (
          <Text className="text-caption text-text-dim">
            📅 Calendar isn&apos;t connected, so this plan doesn&apos;t know about your meetings.
          </Text>
        )}

        {proposal.assignments.length === 0 ? (
          <View className="rounded-card border border-border/20 bg-bg p-4">
            <Text className="text-caption text-text-dim">
              Nothing to schedule — your tray is empty or the day is full.
            </Text>
          </View>
        ) : (
          proposal.assignments.map((a) => {
            const isDropped = !!dropped[a.task_id];
            const time = moved[a.task_id] ?? a.scheduled_time;
            return (
              <View
                key={a.task_id}
                className={`flex-row items-center gap-3 rounded-card border border-border/20 bg-bg p-3 ${
                  isDropped ? "opacity-40" : ""
                }`}
              >
                <View className="w-16">
                  <Text className="text-caption font-semibold text-primary">
                    {hourLabel(time)}
                  </Text>
                </View>
                <View className="flex-1">
                  <Text className="text-body text-text" numberOfLines={1}>
                    {a.title}
                  </Text>
                  <Badge label={a.priority} tone={a.priority} />
                </View>
                {!isDropped && (
                  <View className="flex-row items-center">
                    <Pressable
                      onPress={() => shift(a, -1)}
                      accessibilityLabel={`Move ${a.title} earlier`}
                      className="px-2 py-1 active:opacity-60"
                    >
                      <Text className="text-body text-text-dim">▴</Text>
                    </Pressable>
                    <Pressable
                      onPress={() => shift(a, 1)}
                      accessibilityLabel={`Move ${a.title} later`}
                      className="px-2 py-1 active:opacity-60"
                    >
                      <Text className="text-body text-text-dim">▾</Text>
                    </Pressable>
                  </View>
                )}
                <Pressable
                  onPress={() =>
                    setDropped((prev) => ({ ...prev, [a.task_id]: !prev[a.task_id] }))
                  }
                  accessibilityLabel={`${isDropped ? "Restore" : "Remove"} ${a.title}`}
                  className="rounded-chip bg-primary/10 px-3 py-1.5 active:opacity-80"
                >
                  <Text className="text-caption font-semibold text-primary">
                    {isDropped ? "Undo" : "Skip"}
                  </Text>
                </Pressable>
              </View>
            );
          })
        )}

        {proposal.overflow.length > 0 && (
          <View className="mt-2 gap-2">
            <Text className="text-caption font-semibold uppercase text-text-dim">
              Staying in your tray
            </Text>
            {proposal.overflow.map((o) => (
              <View key={o.task_id} className="rounded-card border border-border/20 p-3">
                <Text className="text-body text-text" numberOfLines={1}>
                  {o.title}
                </Text>
                <Text className="text-caption text-text-dim">{o.reason}</Text>
              </View>
            ))}
          </View>
        )}

        <View className="mt-2 flex-row gap-3">
          <Pressable
            onPress={onReject}
            disabled={applying}
            className="flex-1 items-center rounded-chip border border-border/30 px-4 py-3 active:opacity-80"
          >
            <Text className="text-body font-semibold text-text-dim">Reject</Text>
          </Pressable>
          <Pressable
            onPress={() => onConfirm(kept)}
            disabled={applying || kept.length === 0}
            className={`flex-1 items-center rounded-chip bg-primary px-4 py-3 active:opacity-80 ${
              kept.length === 0 ? "opacity-40" : ""
            }`}
          >
            {applying ? (
              <ActivityIndicator size="small" color="#fff" />
            ) : (
              <Text className="text-body font-semibold text-white">
                Apply {kept.length} task{kept.length === 1 ? "" : "s"}
              </Text>
            )}
          </Pressable>
        </View>
      </BottomSheetScrollView>
    </BottomSheet>
  );
});
