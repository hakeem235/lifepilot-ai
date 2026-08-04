/**
 * Splash — the animated AI orb entry point. Waits for Clerk to load, then routes:
 * signed-in → app shell, signed-out → onboarding. Shown briefly on cold start.
 */
import { useAuth } from "@clerk/clerk-expo";
import { Redirect } from "expo-router";
import { Text, View } from "react-native";
import Animated, { FadeIn } from "react-native-reanimated";

import { AiOrb, GradientBackdrop } from "../components/ui";

export default function Splash() {
  const { isLoaded, isSignedIn } = useAuth();

  if (isLoaded) {
    return <Redirect href={isSignedIn ? "/(tabs)" : "/onboarding"} />;
  }

  return (
    <GradientBackdrop>
      <View className="flex-1 items-center justify-center gap-6">
        <AiOrb size={110} />
        <Animated.View entering={FadeIn.duration(600).delay(200)} className="items-center gap-1">
          <Text className="text-display text-text">LifePilot AI</Text>
          <Text className="text-body text-text-dim">Your Intelligent Daily Companion</Text>
        </Animated.View>
      </View>
    </GradientBackdrop>
  );
}
