/**
 * AiActionMenu — what the floating orb opens.
 *
 * The orb was decorative until the AI Chat tab was removed; it is now the single
 * entry point to the three things the AI actually does (capture, plan, review).
 * Actions that live on another screen navigate there and auto-open, so the orb
 * is a shortcut rather than a second implementation of each flow.
 */
import BottomSheet, { BottomSheetBackdrop, BottomSheetView } from "@gorhom/bottom-sheet";
import { forwardRef, useCallback } from "react";
import { Pressable, Text, View } from "react-native";

import { AI_ACTIONS, type AiActionId } from "../lib/aiActions";
import { useTheme } from "../theme/ThemeProvider";

export type AiActionMenuRef = BottomSheet;

export const AiActionMenu = forwardRef<BottomSheet, { onSelect: (id: AiActionId) => void }>(
  function AiActionMenu({ onSelect }, ref) {
    const { colors } = useTheme();

    const renderBackdrop = useCallback(
      (props: React.ComponentProps<typeof BottomSheetBackdrop>) => (
        <BottomSheetBackdrop {...props} disappearsOnIndex={-1} appearsOnIndex={0} />
      ),
      [],
    );

    return (
      <BottomSheet
        ref={ref}
        index={-1}
        snapPoints={[330]}
        enablePanDownToClose
        backdropComponent={renderBackdrop}
        backgroundStyle={{ backgroundColor: colors.card }}
        handleIndicatorStyle={{ backgroundColor: colors.textDim }}
      >
        <BottomSheetView style={{ padding: 20, gap: 8 }}>
          <Text className="text-title text-text">What can I do?</Text>
          <Text className="mb-1 text-caption text-text-dim">
            Every one of these shows you a preview before anything changes.
          </Text>

          {AI_ACTIONS.map((action) => (
            <Pressable
              key={action.id}
              accessibilityRole="button"
              accessibilityLabel={action.label}
              accessibilityHint={action.description}
              onPress={() => onSelect(action.id)}
              className="flex-row items-center gap-3 rounded-card border border-border/15 px-4 py-3 active:opacity-80"
            >
              <View className="h-10 w-10 items-center justify-center rounded-full bg-primary/10">
                <Text className="text-body">{action.icon}</Text>
              </View>
              <View className="flex-1">
                <Text className="text-body font-semibold text-text">{action.label}</Text>
                <Text className="text-caption text-text-dim">{action.description}</Text>
              </View>
              <Text className="text-caption text-text-dim">›</Text>
            </Pressable>
          ))}
        </BottomSheetView>
      </BottomSheet>
    );
  },
);
