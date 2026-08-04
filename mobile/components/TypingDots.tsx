/** TypingDots — three dots that pulse in sequence (assistant "thinking"). */
import { useEffect } from "react";
import { View } from "react-native";
import Animated, {
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withRepeat,
  withTiming,
} from "react-native-reanimated";

function Dot({ delay }: { delay: number }) {
  const v = useSharedValue(0);
  useEffect(() => {
    v.value = withDelay(
      delay,
      withRepeat(withTiming(1, { duration: 500, easing: Easing.inOut(Easing.ease) }), -1, true),
    );
  }, [delay, v]);
  const style = useAnimatedStyle(() => ({
    opacity: 0.3 + v.value * 0.7,
    transform: [{ translateY: -v.value * 3 }],
  }));
  return <Animated.View style={style} className="h-2 w-2 rounded-full bg-text-dim" />;
}

export function TypingDots() {
  return (
    <View className="flex-row items-center gap-1 py-1">
      <Dot delay={0} />
      <Dot delay={150} />
      <Dot delay={300} />
    </View>
  );
}
