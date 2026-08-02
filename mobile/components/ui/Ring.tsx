/**
 * Ring — circular progress indicator (prototype habit-streak / health rings).
 * SVG-free: two arcs approximated with a rotating border track so the scaffold
 * has no extra native dep. Replaced with an SVG ring if precision is needed later.
 * value: 0–100.
 */
import { Text, View } from "react-native";

export function Ring({
  value,
  size = 64,
  label,
}: {
  value: number;
  size?: number;
  label?: string;
}) {
  const clamped = Math.max(0, Math.min(100, value));
  return (
    <View style={{ width: size, height: size }} className="items-center justify-center">
      <View
        style={{ width: size, height: size, borderRadius: size / 2 }}
        className="absolute border-[6px] border-text-dim/15"
      />
      <View
        style={{
          width: size,
          height: size,
          borderRadius: size / 2,
          transform: [{ rotate: `${(clamped / 100) * 360}deg` }],
        }}
        className="absolute border-[6px] border-transparent border-t-primary"
      />
      {label ? <Text className="text-caption font-semibold text-text">{label}</Text> : null}
    </View>
  );
}
