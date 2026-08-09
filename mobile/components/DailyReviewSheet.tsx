/**
 * DailyReviewSheet — the evening review and roll-forward (Issue 10.2, D10).
 *
 * Shows what actually happened today, then offers to move what slipped into
 * tomorrow. The moves are proposals: the user skips the ones they don't want and
 * confirms the rest, and nothing on the timeline changes until they do.
 *
 * Reuses the plan-preview logic so "skip this one" behaves identically to the
 * auto-scheduler's preview — one mental model for both AI surfaces.
 */
import { BottomSheetModal, BottomSheetBackdrop, BottomSheetScrollView } from "@gorhom/bottom-sheet";
import { forwardRef, useCallback, useMemo, useState } from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";

import { Badge, ProgressBar } from "./ui";
import { describeTime } from "../lib/capture";
import { keptAssignments } from "../lib/planPreview";
import type { DailyReview, PlanAssignment } from "../lib/types";

export const DailyReviewSheet = forwardRef<
  BottomSheetModal,
  {
    review: DailyReview | null;
    loading: boolean;
    applying: boolean;
    onConfirm: (moves: PlanAssignment[]) => void;
    onClose: () => void;
  }
>(function DailyReviewSheet({ review, loading, applying, onConfirm, onClose }, ref) {
  const [dropped, setDropped] = useState<Record<string, boolean>>({});

  const renderBackdrop = useCallback(
    (props: React.ComponentProps<typeof BottomSheetBackdrop>) => (
      <BottomSheetBackdrop {...props} disappearsOnIndex={-1} appearsOnIndex={0} />
    ),
    [],
  );

  const kept = useMemo<PlanAssignment[]>(
    () => (review ? keptAssignments(review.proposed_moves, dropped, {}) : []),
    [review, dropped],
  );

  return (
    <BottomSheetModal
      ref={ref}
      snapPoints={["70%"]}
      enablePanDownToClose
      onDismiss={() => {
        setDropped({});
        onClose();
      }}
      backdropComponent={renderBackdrop}
    >
      <BottomSheetScrollView contentContainerStyle={{ padding: 20, gap: 12 }}>
        {loading || !review ? (
          <ActivityIndicator />
        ) : (
          <>
            <Text className="text-title text-text">Today&apos;s review</Text>
            <Text className="text-body text-text">{review.summary}</Text>

            <View className="gap-1">
              <View className="flex-row justify-between">
                <Text className="text-caption text-text-dim">
                  {review.done.length} done · {review.slipped.length} slipped
                </Text>
                <Text className="text-caption font-semibold text-primary">
                  {review.completion_rate}%
                </Text>
              </View>
              <ProgressBar value={review.completion_rate} />
            </View>

            {review.done.length > 0 && (
              <View className="gap-1">
                <Text className="text-caption font-semibold uppercase text-text-dim">
                  Completed
                </Text>
                {review.done.map((t) => (
                  <Text key={t.task_id} className="text-body text-text-dim" numberOfLines={1}>
                    ✓ {t.title}
                  </Text>
                ))}
              </View>
            )}

            {review.proposed_moves.length > 0 && (
              <View className="gap-2">
                <Text className="text-caption font-semibold uppercase text-text-dim">
                  Move to tomorrow
                </Text>
                {review.proposed_moves.map((m) => {
                  const isDropped = !!dropped[m.task_id];
                  return (
                    <View
                      key={m.task_id}
                      className={`flex-row items-center gap-3 rounded-card border border-border/20 bg-bg p-3 ${
                        isDropped ? "opacity-40" : ""
                      }`}
                    >
                      <Text className="w-16 text-caption font-semibold text-primary">
                        {describeTime(m.scheduled_time)}
                      </Text>
                      <View className="flex-1">
                        <Text className="text-body text-text" numberOfLines={1}>
                          {m.title}
                        </Text>
                        <Badge label={m.priority} tone={m.priority} />
                      </View>
                      <Pressable
                        onPress={() =>
                          setDropped((prev) => ({ ...prev, [m.task_id]: !prev[m.task_id] }))
                        }
                        accessibilityLabel={`${isDropped ? "Restore" : "Skip"} ${m.title}`}
                        className="rounded-chip bg-primary/10 px-3 py-1.5 active:opacity-80"
                      >
                        <Text className="text-caption font-semibold text-primary">
                          {isDropped ? "Undo" : "Skip"}
                        </Text>
                      </Pressable>
                    </View>
                  );
                })}
              </View>
            )}

            {review.overflow.length > 0 && (
              <View className="gap-1">
                <Text className="text-caption font-semibold uppercase text-text-dim">
                  No room tomorrow
                </Text>
                {review.overflow.map((o) => (
                  <Text key={o.task_id} className="text-caption text-text-dim">
                    {o.title} — {o.reason}
                  </Text>
                ))}
              </View>
            )}

            {review.slipped.length === 0 ? (
              <Text className="text-caption text-text-dim">
                Nothing slipped — there&apos;s nothing to roll forward.
              </Text>
            ) : (
              <Pressable
                onPress={() => onConfirm(kept)}
                disabled={applying || kept.length === 0}
                className={`mt-2 items-center rounded-chip bg-primary px-4 py-3 active:opacity-80 ${
                  kept.length === 0 ? "opacity-40" : ""
                }`}
              >
                {applying ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text className="text-body font-semibold text-white">
                    Move {kept.length} task{kept.length === 1 ? "" : "s"} to tomorrow
                  </Text>
                )}
              </Pressable>
            )}
          </>
        )}
      </BottomSheetScrollView>
    </BottomSheetModal>
  );
});
