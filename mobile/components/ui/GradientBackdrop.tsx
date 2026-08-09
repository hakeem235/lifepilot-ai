/**
 * GradientBackdrop — the ambient gradient behind every screen. Two soft radial-ish
 * blobs (via overlapping linear gradients) over the themed background, giving the
 * "ambient gradient backdrop" look without a heavy shader.
 */
import { LinearGradient } from "expo-linear-gradient";
import { StyleSheet, View } from "react-native";

import { useTheme } from "../../theme/ThemeProvider";

export function GradientBackdrop({ children }: { children: React.ReactNode }) {
  const { name } = useTheme();
  const tint =
    name === "dark"
      ? { a: "rgba(79,70,229,0.28)", b: "rgba(124,58,237,0.20)" }
      : { a: "rgba(79,70,229,0.14)", b: "rgba(6,182,212,0.10)" };
  return (
    <View className="flex-1 bg-bg">
      {/*
        Both blobs fill the whole backdrop and fade via their own colour stops.

        They used to be fixed-height boxes (420 / 360). That failed twice over:
        on a screen taller than 780pt the two never met, leaving a strip of flat
        `bg-bg` between them, and because the tint only reaches `transparent` at
        the *end* of a diagonal, clipping the box left a hard edge along its
        bottom — a pale rectangle across the page, worst on the left where the
        tint is strongest. With no element boundary inside the screen there is
        no edge to see, at any screen size.
      */}
      <LinearGradient
        colors={[tint.a, "transparent"]}
        locations={[0, 0.55]}
        start={{ x: 0, y: 0 }}
        end={{ x: 0.9, y: 0.85 }}
        style={StyleSheet.absoluteFill}
      />
      <LinearGradient
        colors={["transparent", tint.b]}
        locations={[0.45, 1]}
        start={{ x: 1, y: 0.15 }}
        end={{ x: 0, y: 1 }}
        style={StyleSheet.absoluteFill}
      />
      {children}
    </View>
  );
}
