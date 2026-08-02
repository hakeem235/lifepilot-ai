/** ProgressBar — task progress track (prototype progress). value: 0–100. */
import { View } from "react-native";

export function ProgressBar({ value }: { value: number }) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <View className="h-2 w-full overflow-hidden rounded-chip bg-text-dim/15">
      <View className="h-full rounded-chip bg-primary" style={{ width: `${clamped}%` }} />
    </View>
  );
}
