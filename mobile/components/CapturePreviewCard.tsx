/**
 * CapturePreviewCard — the confirm gate for natural-language capture (Issue 10.1, D10).
 *
 * Sits above the capture input holding a drafted task. The title stays editable, so
 * a near-miss is a one-tap fix rather than a retype, and the date/time read back
 * in words ("Tomorrow · 2:00 PM") so the user can see what was understood before
 * agreeing to it. No task exists until "Add task".
 */
import { useEffect, useState } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View } from "react-native";

import { Badge } from "./ui";
import { describeDraft } from "../lib/capture";
import { todayISO } from "../lib/date";
import type { CaptureDraft, CaptureProposal } from "../lib/types";
import { useTheme } from "../theme/ThemeProvider";

export function CapturePreviewCard({
  proposal,
  saving,
  onConfirm,
  onDiscard,
}: {
  proposal: CaptureProposal;
  saving: boolean;
  onConfirm: (draft: CaptureDraft) => void;
  onDiscard: () => void;
}) {
  const { colors } = useTheme();
  const [title, setTitle] = useState(proposal.draft?.title ?? "");

  // A fresh parse replaces whatever was being edited.
  useEffect(() => {
    setTitle(proposal.draft?.title ?? "");
  }, [proposal.draft?.title]);

  if (!proposal.draft) {
    return (
      <View className="mx-4 mb-2 rounded-card border border-border/20 bg-card p-3">
        <Text className="text-caption text-text-dim">
          I couldn&apos;t find a task in that. Try something like &ldquo;call the dentist
          tomorrow at 2pm&rdquo;.
        </Text>
        <Pressable onPress={onDiscard} className="mt-2 self-start active:opacity-60">
          <Text className="text-caption font-semibold text-primary">Dismiss</Text>
        </Pressable>
      </View>
    );
  }

  const summary = describeDraft(proposal.draft, todayISO());

  return (
    <View className="mx-4 mb-2 rounded-card border border-primary/30 bg-card p-3">
      <View className="mb-2 flex-row items-center justify-between">
        <Text className="text-caption font-semibold uppercase text-primary">New task</Text>
        {proposal.generated_by === "fallback" && <Badge label="offline" tone="low" />}
      </View>

      <TextInput
        className="rounded-chip border border-border/20 bg-bg px-3 py-2 text-body text-text"
        value={title}
        onChangeText={setTitle}
        placeholder="Task title"
        placeholderTextColor={colors.textDim}
        accessibilityLabel="Task title"
      />

      {summary !== "" && <Text className="mt-2 text-caption text-text-dim">{summary}</Text>}

      {proposal.generated_by === "fallback" && (
        <Text className="mt-2 text-caption text-text-dim">
          Offline — I kept your wording but didn&apos;t set a date. You can add one after.
        </Text>
      )}

      {proposal.slot_conflict && (
        <Text className="mt-2 text-caption text-text-dim">
          That hour is already taken — I&apos;ll add this to your tray instead.
        </Text>
      )}

      <View className="mt-3 flex-row gap-2">
        <Pressable
          onPress={onDiscard}
          disabled={saving}
          className="rounded-chip border border-border/30 px-4 py-2 active:opacity-80"
        >
          <Text className="text-caption font-semibold text-text-dim">Discard</Text>
        </Pressable>
        <Pressable
          onPress={() => onConfirm({ ...proposal.draft!, title: title.trim() })}
          disabled={saving || title.trim() === ""}
          className={`flex-1 items-center rounded-chip bg-primary px-4 py-2 active:opacity-80 ${
            title.trim() === "" ? "opacity-40" : ""
          }`}
        >
          {saving ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text className="text-caption font-semibold text-white">Add task</Text>
          )}
        </Pressable>
      </View>
    </View>
  );
}
