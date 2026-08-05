/**
 * UndoBanner — the visible half of reversibility (Issue 10.3).
 *
 * Appears after an AI change lands and offers to walk it back. It matters more
 * than it looks: confirming a whole day's plan is only a low-stakes tap if the
 * user can see, immediately, that it isn't permanent.
 *
 * Dismissing hides the offer; it doesn't undo. The change stays applied either way.
 */
import { ActivityIndicator, Pressable, Text, View } from "react-native";

export function UndoBanner({
  label,
  undoing,
  onUndo,
  onDismiss,
}: {
  label: string;
  undoing: boolean;
  onUndo: () => void;
  onDismiss: () => void;
}) {
  return (
    <View className="mx-4 mb-2 flex-row items-center gap-3 rounded-card border border-border/20 bg-card p-3">
      <Text className="flex-1 text-caption text-text" numberOfLines={2}>
        {label}
      </Text>
      <Pressable
        onPress={onUndo}
        disabled={undoing}
        accessibilityLabel="Undo"
        className="rounded-chip bg-primary/10 px-3 py-1.5 active:opacity-80"
      >
        {undoing ? (
          <ActivityIndicator size="small" />
        ) : (
          <Text className="text-caption font-semibold text-primary">Undo</Text>
        )}
      </Pressable>
      <Pressable onPress={onDismiss} accessibilityLabel="Dismiss" className="px-1 active:opacity-60">
        <Text className="text-caption text-text-dim">✕</Text>
      </Pressable>
    </View>
  );
}
