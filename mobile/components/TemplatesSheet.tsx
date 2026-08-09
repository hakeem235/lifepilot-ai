/**
 * TemplatesSheet — slide-up sheet listing routines (system presets + own).
 * Tapping Apply lays the routine's tasks onto the given day, then closes and
 * lets the Planner refresh so the new tasks appear on the timeline (Issue 9.1).
 */
import { BottomSheetModal, BottomSheetBackdrop, BottomSheetScrollView } from "@gorhom/bottom-sheet";
import { forwardRef, useCallback, useState } from "react";
import { ActivityIndicator, Pressable, Text, View } from "react-native";

import { useTemplates } from "../lib/hooks";
import { brand } from "../theme/tokens";
import { useTheme } from "../theme/ThemeProvider";

export const TemplatesSheet = forwardRef<
  BottomSheetModal,
  { dateISO: string; onApplied: () => void }
>(function TemplatesSheet({ dateISO, onApplied }, ref) {
  const { colors } = useTheme();
  const { templates, loading, apply } = useTemplates();
  const [applyingId, setApplyingId] = useState<string | null>(null);

  const renderBackdrop = useCallback(
    (props: React.ComponentProps<typeof BottomSheetBackdrop>) => (
      <BottomSheetBackdrop {...props} disappearsOnIndex={-1} appearsOnIndex={0} />
    ),
    [],
  );

  const onApply = async (id: string) => {
    setApplyingId(id);
    const ok = await apply(id, dateISO);
    setApplyingId(null);
    if (ok) {
      (ref as React.RefObject<BottomSheetModal>)?.current?.dismiss();
      onApplied();
    }
  };

  return (
    <BottomSheetModal
      ref={ref}
      snapPoints={["55%"]}
      enablePanDownToClose
      backdropComponent={renderBackdrop}
      backgroundStyle={{ backgroundColor: colors.card }}
      handleIndicatorStyle={{ backgroundColor: colors.textDim }}
    >
      <BottomSheetScrollView contentContainerStyle={{ padding: 20, gap: 12 }}>
        <Text className="text-title text-text">Routines</Text>
        <Text className="text-caption text-text-dim">
          Apply a routine to lay its tasks onto today&apos;s timeline.
        </Text>
        {loading ? (
          <ActivityIndicator color={brand.primary} />
        ) : (
          templates.map((tpl) => (
            <View
              key={tpl.id}
              className="flex-row items-center gap-3 rounded-card border border-border/20 bg-bg p-4"
            >
              <Text className="text-title">{tpl.icon || "📋"}</Text>
              <View className="flex-1">
                <Text className="text-body font-semibold text-text">{tpl.name}</Text>
                <Text className="text-caption text-text-dim" numberOfLines={1}>
                  {tpl.items.length} task{tpl.items.length === 1 ? "" : "s"}
                  {tpl.is_preset ? " · preset" : ""}
                </Text>
              </View>
              <Pressable
                disabled={applyingId !== null}
                onPress={() => onApply(tpl.id)}
                className="rounded-chip bg-primary px-4 py-2 active:opacity-80"
              >
                {applyingId === tpl.id ? (
                  <ActivityIndicator size="small" color="#fff" />
                ) : (
                  <Text className="text-caption font-semibold text-white">Apply</Text>
                )}
              </Pressable>
            </View>
          ))
        )}
      </BottomSheetScrollView>
    </BottomSheetModal>
  );
});
