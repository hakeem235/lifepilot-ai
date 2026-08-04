/**
 * AiOrb — the glowing, breathing AI logo/mark. A gradient sphere with a soft halo
 * that pulses (scale + glow) on a loop. Respects reduced-motion (renders static).
 * Used large on Splash and small as the floating FAB.
 */
import { LinearGradient } from "expo-linear-gradient";
import { useEffect } from "react";
import { AccessibilityInfo, View } from "react-native";
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withRepeat,
  withTiming,
} from "react-native-reanimated";

import { brand } from "../../theme/tokens";

export function AiOrb({ size = 96 }: { size?: number }) {
  const pulse = useSharedValue(0);

  useEffect(() => {
    let cancelled = false;
    AccessibilityInfo.isReduceMotionEnabled().then((reduced) => {
      if (cancelled || reduced) return;
      pulse.value = withRepeat(
        withTiming(1, { duration: 2200, easing: Easing.inOut(Easing.ease) }),
        -1,
        true,
      );
    });
    return () => {
      cancelled = true;
    };
  }, [pulse]);

  const haloStyle = useAnimatedStyle(() => ({
    opacity: 0.35 + pulse.value * 0.35,
    transform: [{ scale: 1 + pulse.value * 0.18 }],
  }));
  const coreStyle = useAnimatedStyle(() => ({
    transform: [{ scale: 1 + pulse.value * 0.05 }],
  }));

  return (
    <View style={{ width: size * 1.6, height: size * 1.6 }} className="items-center justify-center">
      <Animated.View
        style={[
          {
            position: "absolute",
            width: size * 1.5,
            height: size * 1.5,
            borderRadius: size,
            backgroundColor: brand.primary,
          },
          haloStyle,
        ]}
      />
      <Animated.View
        style={[
          { width: size, height: size, borderRadius: size / 2, overflow: "hidden" },
          coreStyle,
        ]}
      >
        <LinearGradient
          colors={[brand.primary, brand.secondary]}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={{ flex: 1 }}
        />
      </Animated.View>
    </View>
  );
}
