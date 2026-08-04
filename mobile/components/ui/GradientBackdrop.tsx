/**
 * GradientBackdrop — the ambient gradient behind every screen. Two soft radial-ish
 * blobs (via overlapping linear gradients) over the themed background, giving the
 * "ambient gradient backdrop" look without a heavy shader.
 */
import { LinearGradient } from "expo-linear-gradient";
import { View } from "react-native";

import { useTheme } from "../../theme/ThemeProvider";

export function GradientBackdrop({ children }: { children: React.ReactNode }) {
  const { name } = useTheme();
  const tint =
    name === "dark"
      ? { a: "rgba(79,70,229,0.28)", b: "rgba(124,58,237,0.20)" }
      : { a: "rgba(79,70,229,0.14)", b: "rgba(6,182,212,0.10)" };
  return (
    <View className="flex-1 bg-bg">
      <LinearGradient
        colors={[tint.a, "transparent"]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 0.6 }}
        style={{ position: "absolute", left: 0, right: 0, top: 0, height: 420 }}
      />
      <LinearGradient
        colors={["transparent", tint.b]}
        start={{ x: 1, y: 0.4 }}
        end={{ x: 0, y: 1 }}
        style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 360 }}
      />
      {children}
    </View>
  );
}
