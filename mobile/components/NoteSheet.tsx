/**
 * NoteSheet — create or edit a note.
 *
 * Title is optional: most quick notes are just a body, and the server derives a
 * display title from the first line rather than forcing a title at capture time.
 * The Save button mirrors the server's rule (a note needs a title or a body) so
 * an empty note is refused before it costs a round trip.
 */
import { BottomSheetModal, BottomSheetBackdrop, BottomSheetView } from "@gorhom/bottom-sheet";
import { forwardRef, useEffect, useState } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View } from "react-native";

import type { Note } from "../lib/types";
import { useTheme } from "../theme/ThemeProvider";

export type NoteSheetRef = BottomSheetModal;

export const NoteSheet = forwardRef<
  BottomSheetModal,
  {
    /** The note being edited, or null to compose a new one. */
    note: Note | null;
    saving: boolean;
    onSave: (input: { id?: string; title: string; body: string }) => void;
    onDelete?: (id: string) => void;
  }
>(function NoteSheet({ note, saving, onSave, onDelete }, ref) {
  const { colors } = useTheme();
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");

  // Reload the fields whenever a different note is opened. Keyed on id so
  // typing is never clobbered by a refetch that returns the same note.
  useEffect(() => {
    setTitle(note?.title ?? "");
    setBody(note?.body ?? "");
  }, [note?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const canSave = (title.trim().length > 0 || body.trim().length > 0) && !saving;

  return (
    <BottomSheetModal
      ref={ref}
      snapPoints={["75%"]}
      enablePanDownToClose
      backdropComponent={(props) => (
        <BottomSheetBackdrop {...props} disappearsOnIndex={-1} appearsOnIndex={0} />
      )}
      backgroundStyle={{ backgroundColor: colors.card }}
      handleIndicatorStyle={{ backgroundColor: colors.textDim }}
    >
      <BottomSheetView style={{ padding: 20, gap: 12 }}>
        <View className="flex-row items-center justify-between">
          <Text className="text-title text-text">{note ? "Edit note" : "New note"}</Text>
          {note && onDelete && (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Delete note"
              onPress={() => onDelete(note.id)}
              className="rounded-chip border border-danger/30 px-3 py-1.5 active:opacity-80"
            >
              <Text className="text-caption font-medium text-danger">Delete</Text>
            </Pressable>
          )}
        </View>

        <TextInput
          placeholder="Title (optional)"
          placeholderTextColor={colors.textDim}
          value={title}
          onChangeText={setTitle}
          accessibilityLabel="Note title"
          className="rounded-card border border-border/20 bg-bg px-4 py-3 text-body text-text"
        />

        <TextInput
          autoFocus={!note}
          placeholder="Write your note…"
          placeholderTextColor={colors.textDim}
          value={body}
          onChangeText={setBody}
          multiline
          textAlignVertical="top"
          accessibilityLabel="Note body"
          className="h-44 rounded-card border border-border/20 bg-bg px-4 py-3 text-body text-text"
        />

        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Save note"
          disabled={!canSave}
          onPress={() => onSave({ id: note?.id, title: title.trim(), body: body.trim() })}
          className={`items-center rounded-card py-4 ${
            canSave ? "bg-primary active:opacity-80" : "bg-primary/30"
          }`}
        >
          {saving ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text className="text-body font-semibold text-white">Save</Text>
          )}
        </Pressable>

        {!canSave && !saving && (
          <Text className="text-center text-caption text-text-dim">
            Add a title or some text to save.
          </Text>
        )}
      </BottomSheetView>
    </BottomSheetModal>
  );
});
