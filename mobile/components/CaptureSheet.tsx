/**
 * CaptureSheet — natural-language capture (Issue 10.1), relocated here from the
 * Chat tab when that tab was removed.
 *
 * Type a sentence ("call the dentist tomorrow 2pm"), it is parsed server-side
 * into a structured draft, and the draft is shown as a preview the user must
 * confirm before any Task is written (D10). This sheet owns the input; the
 * preview and undo affordances stay in their existing components.
 */
import BottomSheet, { BottomSheetBackdrop, BottomSheetView } from "@gorhom/bottom-sheet";
import { forwardRef, useCallback, useState } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View } from "react-native";

import { CapturePreviewCard } from "./CapturePreviewCard";
import { UndoBanner } from "./UndoBanner";
import { useCapture, useUndo } from "../lib/hooks";
import type { CaptureDraft } from "../lib/types";
import { useTheme } from "../theme/ThemeProvider";

const EXAMPLES = [
  "Call the dentist tomorrow 2pm",
  "Submit the report Friday",
  "Buy groceries",
];

export type CaptureSheetRef = BottomSheet;

export const CaptureSheet = forwardRef<BottomSheet, { onCaptured?: () => void }>(
  function CaptureSheet({ onCaptured }, ref) {
    const { colors } = useTheme();
    const { proposal, parsing, saving, parse, confirm, discard } = useCapture();
    // A captured task is reversed by deleting it, so undo carries its id (10.3).
    const { pending: undoOffer, undoing, offer, undo, clear: clearUndo } = useUndo();
    const [text, setText] = useState("");

    const renderBackdrop = useCallback(
      (props: React.ComponentProps<typeof BottomSheetBackdrop>) => (
        <BottomSheetBackdrop {...props} disappearsOnIndex={-1} appearsOnIndex={0} />
      ),
      [],
    );

    const submit = (value?: string) => {
      const msg = (value ?? text).trim();
      if (!msg || parsing) return;
      setText("");
      clearUndo();
      void parse(msg);
    };

    const onConfirm = async (draft: CaptureDraft) => {
      const task = await confirm(draft);
      if (task) {
        offer(`Added “${task.title}”.`, [], [task.id]);
        onCaptured?.();
      }
    };

    return (
      <BottomSheet
        ref={ref}
        index={-1}
        snapPoints={[380]}
        enablePanDownToClose
        backdropComponent={renderBackdrop}
        backgroundStyle={{ backgroundColor: colors.card }}
        handleIndicatorStyle={{ backgroundColor: colors.textDim }}
      >
        <BottomSheetView style={{ padding: 20, gap: 12 }}>
          <Text className="text-title text-text">Quick capture</Text>
          <Text className="text-caption text-text-dim">
            Write it the way you&apos;d say it — I&apos;ll turn it into a task for you to
            confirm.
          </Text>

          <View className="flex-row items-center gap-2">
            <TextInput
              autoFocus
              placeholder="e.g. Call the dentist tomorrow 2pm"
              placeholderTextColor={colors.textDim}
              value={text}
              onChangeText={setText}
              onSubmitEditing={() => submit()}
              returnKeyType="done"
              accessibilityLabel="Task description"
              className="flex-1 rounded-card border border-border/20 bg-bg px-4 py-3 text-body text-text"
            />
            <Pressable
              accessibilityLabel="Capture as task"
              onPress={() => submit()}
              disabled={!text.trim() || parsing}
              className="h-11 w-11 items-center justify-center rounded-full bg-primary disabled:opacity-40"
            >
              {parsing ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <Text className="text-body font-semibold text-white">＋</Text>
              )}
            </Pressable>
          </View>

          {proposal === null && !parsing && (
            <View className="flex-row flex-wrap gap-2">
              {EXAMPLES.map((example) => (
                <Pressable
                  key={example}
                  onPress={() => submit(example)}
                  className="rounded-chip border border-primary/30 bg-primary/10 px-3 py-1.5"
                >
                  <Text className="text-caption font-medium text-primary">{example}</Text>
                </Pressable>
              ))}
            </View>
          )}

          {undoOffer !== null && proposal === null && (
            <UndoBanner
              label={undoOffer.label}
              undoing={undoing}
              onUndo={undo}
              onDismiss={clearUndo}
            />
          )}

          {proposal !== null && (
            <CapturePreviewCard
              proposal={proposal}
              saving={saving}
              onConfirm={onConfirm}
              onDiscard={discard}
            />
          )}
        </BottomSheetView>
      </BottomSheet>
    );
  },
);
