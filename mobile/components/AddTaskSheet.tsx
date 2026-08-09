/**
 * AddTaskSheet — slide-up bottom sheet to create a task (title + priority).
 * Wired to the API via the onAdd callback (optimistic refresh handled upstream).
 */
import { BottomSheetModal, BottomSheetBackdrop, BottomSheetView } from "@gorhom/bottom-sheet";
import { forwardRef, useCallback, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";

import { useTheme } from "../theme/ThemeProvider";
import type { Priority } from "../lib/types";

const PRIORITIES: Priority[] = ["high", "medium", "low"];

export type AddTaskSheetRef = BottomSheetModal;

export const AddTaskSheet = forwardRef<
  BottomSheetModal,
  { onAdd: (title: string, priority: Priority) => void }
>(function AddTaskSheet({ onAdd }, ref) {
  const { colors } = useTheme();
  const [title, setTitle] = useState("");
  const [priority, setPriority] = useState<Priority>("medium");

  const renderBackdrop = useCallback(
    (props: React.ComponentProps<typeof BottomSheetBackdrop>) => (
      <BottomSheetBackdrop {...props} disappearsOnIndex={-1} appearsOnIndex={0} />
    ),
    [],
  );

  const submit = () => {
    const t = title.trim();
    if (!t) return;
    onAdd(t, priority);
    setTitle("");
    setPriority("medium");
    (ref as React.RefObject<BottomSheetModal>)?.current?.dismiss();
  };

  return (
    <BottomSheetModal
      ref={ref}
      snapPoints={[320]}
      enablePanDownToClose
      backdropComponent={renderBackdrop}
      backgroundStyle={{ backgroundColor: colors.card }}
      handleIndicatorStyle={{ backgroundColor: colors.textDim }}
    >
      <BottomSheetView style={{ padding: 20, gap: 16 }}>
        <Text className="text-title text-text">New task</Text>
        <TextInput
          autoFocus
          placeholder="What needs doing?"
          placeholderTextColor={colors.textDim}
          value={title}
          onChangeText={setTitle}
          onSubmitEditing={submit}
          className="rounded-card border border-border/20 bg-bg px-4 py-4 text-body text-text"
        />
        <View className="flex-row gap-2">
          {PRIORITIES.map((p) => (
            <Pressable
              key={p}
              onPress={() => setPriority(p)}
              className={`flex-1 items-center rounded-chip border py-2 ${
                priority === p ? "border-primary bg-primary/10" : "border-border/20"
              }`}
            >
              <Text
                className={`text-caption font-semibold ${priority === p ? "text-primary" : "text-text-dim"}`}
              >
                {p}
              </Text>
            </Pressable>
          ))}
        </View>
        <Pressable
          onPress={submit}
          className="items-center rounded-card bg-primary py-4 active:opacity-80"
        >
          <Text className="text-body font-semibold text-white">Add task</Text>
        </Pressable>
      </BottomSheetView>
    </BottomSheetModal>
  );
});
