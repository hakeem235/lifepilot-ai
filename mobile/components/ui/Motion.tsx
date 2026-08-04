/**
 * Motion primitives — the "smooth transitions" layer, built on Reanimated 4 layout
 * animations (the RN equivalent of Framer Motion's enter/exit). FadeInUp staggers
 * children into place; all respect reduced-motion via Reanimated's own handling.
 */
import Animated, { FadeIn, FadeInDown } from "react-native-reanimated";

export function FadeInUp({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <Animated.View
      entering={FadeInDown.duration(420).delay(delay).springify().damping(18)}
      className={className}
    >
      {children}
    </Animated.View>
  );
}

export function Fade({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  return (
    <Animated.View entering={FadeIn.duration(300).delay(delay)} className={className}>
      {children}
    </Animated.View>
  );
}
