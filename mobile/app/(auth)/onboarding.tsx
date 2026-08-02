/**
 * Onboarding — 4-screen swipeable intro (PRD §4.1). Horizontal paged scroll with
 * an animated dot indicator that tracks scroll position; last screen advances to
 * login. Messaging: intro, daily-brief automation, proactive nudges, privacy/consent.
 */
import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";
import { useRef, useState } from "react";
import {
  Dimensions,
  type NativeScrollEvent,
  type NativeSyntheticEvent,
  Pressable,
  ScrollView,
  Text,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { AiOrb, GlassCard, GradientBackdrop } from "../../components/ui";

const { width } = Dimensions.get("window");

type Slide = {
  title: string;
  body: string;
  bullets?: string[];
  icon?: "orb";
};

const SLIDES: Slide[] = [
  {
    title: "Your AI Assistant for Everyday Life.",
    body: "One companion that quietly keeps your day on track.",
    icon: "orb",
  },
  {
    title: "Everything, organized automatically",
    body: "LifePilot connects the pieces of your day:",
    bullets: [
      "Emails triaged",
      "Calendar synced",
      "Tasks tracked",
      "Notes captured",
      "Expenses logged",
    ],
  },
  {
    title: "Proactive, not just reactive",
    body: "It reaches out before things slip:",
    bullets: [
      "“Leave now — traffic is heavier than usual”",
      "“Your internet bill is due tomorrow”",
      "“You forgot to reply to Sarah”",
    ],
  },
  {
    title: "Permissions, on your terms",
    body: "Calendar, Email, Notifications, Location, Contacts — each is optional, asked for in context, and revocable any time.",
  },
];

export default function OnboardingScreen() {
  const [index, setIndex] = useState(0);
  const scrollRef = useRef<ScrollView>(null);
  const last = index === SLIDES.length - 1;

  const onScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const i = Math.round(e.nativeEvent.contentOffset.x / width);
    if (i !== index) setIndex(i);
  };

  const next = () => {
    if (last) {
      router.replace("/login");
    } else {
      scrollRef.current?.scrollTo({ x: (index + 1) * width, animated: true });
    }
  };

  return (
    <GradientBackdrop>
      <SafeAreaView className="flex-1">
        <ScrollView
          ref={scrollRef}
          horizontal
          pagingEnabled
          showsHorizontalScrollIndicator={false}
          onScroll={onScroll}
          scrollEventThrottle={16}
        >
          {SLIDES.map((s) => (
            <View key={s.title} style={{ width }} className="flex-1 justify-center px-6">
              {s.icon === "orb" && (
                <View className="mb-8 items-center">
                  <AiOrb size={96} />
                </View>
              )}
              <Text className="text-display text-text">{s.title}</Text>
              <Text className="mt-2 text-body text-text-dim">{s.body}</Text>
              {s.bullets && (
                <GlassCard className="mt-5">
                  <View className="gap-2">
                    {s.bullets.map((b) => (
                      <Text key={b} className="text-body text-text">
                        • {b}
                      </Text>
                    ))}
                  </View>
                </GlassCard>
              )}
            </View>
          ))}
        </ScrollView>

        <View className="px-6 pb-6">
          <View className="mb-5 flex-row justify-center gap-2">
            {SLIDES.map((_, i) => (
              <View
                key={i}
                className={`h-1.5 rounded-chip ${i === index ? "w-6 bg-primary" : "w-1.5 bg-text-dim/30"}`}
              />
            ))}
          </View>
          <Pressable
            accessibilityRole="button"
            onPress={next}
            className="overflow-hidden rounded-card"
          >
            <LinearGradient
              colors={["#4F46E5", "#7C3AED"]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
            >
              <Text className="py-4 text-center text-body font-semibold text-white">
                {last ? "Get started" : "Continue"}
              </Text>
            </LinearGradient>
          </Pressable>
          {!last && (
            <Pressable
              accessibilityRole="button"
              onPress={() => router.replace("/login")}
              className="items-center py-3"
            >
              <Text className="text-body text-text-dim">Skip</Text>
            </Pressable>
          )}
        </View>
      </SafeAreaView>
    </GradientBackdrop>
  );
}
