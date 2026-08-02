/** Badge — priority / status indicator (prototype high/med/low badges). */
import { Text, View } from "react-native";

type Tone = "high" | "medium" | "low" | "neutral";

const toneClass: Record<Tone, string> = {
  high: "bg-danger/15",
  medium: "bg-warning/15",
  low: "bg-success/15",
  neutral: "bg-text-dim/15",
};

const textClass: Record<Tone, string> = {
  high: "text-danger",
  medium: "text-warning",
  low: "text-success",
  neutral: "text-text-dim",
};

export function Badge({ label, tone = "neutral" }: { label: string; tone?: Tone }) {
  return (
    <View className={`rounded-chip px-2 py-0.5 ${toneClass[tone]}`}>
      <Text className={`text-caption font-semibold ${textClass[tone]}`}>{label}</Text>
    </View>
  );
}
