import { Pressable, Text, View } from "react-native";

export function Chip({
  label,
  className = "",
  onPress,
}: {
  label: string;
  className?: string;
  onPress?: () => void;
}) {
  const body = (
    <View className={`rounded-chip bg-primary/10 px-3 py-1.5 ${className}`}>
      <Text className="text-caption font-medium text-primary">{label}</Text>
    </View>
  );

  // Stays a plain View when there is nothing to press, so the decorative chips
  // don't announce themselves as buttons to a screen reader.
  if (!onPress) return body;

  return (
    <Pressable accessibilityRole="button" accessibilityLabel={label} onPress={onPress}>
      {body}
    </Pressable>
  );
}
