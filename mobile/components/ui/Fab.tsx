/** Fab — floating action button (prototype voice/mic FAB). */
import { Pressable, Text } from "react-native";

export function Fab({
  label = "＋",
  onPress,
  accessibilityLabel,
}: {
  label?: string;
  onPress?: () => void;
  accessibilityLabel?: string;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? "Action"}
      onPress={onPress}
      className="absolute bottom-6 right-6 h-14 w-14 items-center justify-center rounded-full bg-primary shadow-lg active:opacity-80"
    >
      <Text className="text-2xl font-semibold text-white">{label}</Text>
    </Pressable>
  );
}
