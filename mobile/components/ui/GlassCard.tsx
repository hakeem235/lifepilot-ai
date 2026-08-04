/**
 * GlassCard — glassmorphism surface: a blurred, translucent panel with a hairline
 * border. Uses expo-blur; on platforms/here where blur is unavailable it degrades
 * to a semi-opaque card (still readable).
 */
import { BlurView } from "expo-blur";
import { View, type ViewProps } from "react-native";

import { useTheme } from "../../theme/ThemeProvider";

export function GlassCard({
  className = "",
  intensity = 40,
  children,
  ...props
}: ViewProps & { className?: string; intensity?: number }) {
  const { name } = useTheme();
  return (
    <View
      className={`overflow-hidden rounded-card border border-border/15 ${className}`}
      {...props}
    >
      <BlurView
        intensity={intensity}
        tint={name === "dark" ? "dark" : "light"}
        style={{ position: "absolute", inset: 0 }}
      />
      <View className={name === "dark" ? "bg-card/40" : "bg-card/60"}>
        <View className="p-4">{children}</View>
      </View>
    </View>
  );
}
