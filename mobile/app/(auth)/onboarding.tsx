/**
 * Onboarding — 4 steps per PRD §4.1. Pure presentation; permissions themselves
 * are requested contextually later (consent-first, step 4 just explains that).
 */
import { router } from "expo-router";
import { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { Card } from "../../components/ui";

const STEPS = [
  {
    title: "Your AI Assistant for Everyday Life.",
    body: "One companion that quietly keeps your day on track.",
    bullets: [],
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
    bullets: [],
  },
] as const;

export default function OnboardingScreen() {
  const [step, setStep] = useState(0);
  const current = STEPS[step];
  const last = step === STEPS.length - 1;

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <View className="flex-1 justify-between px-6 py-8">
        <View className="flex-row justify-center gap-2">
          {STEPS.map((_, i) => (
            <View
              key={i}
              className={`h-1.5 rounded-chip ${i === step ? "w-6 bg-primary" : "w-1.5 bg-text-dim/30"}`}
            />
          ))}
        </View>

        <View className="gap-4">
          <Text className="text-display text-text">{current.title}</Text>
          <Text className="text-body text-text-dim">{current.body}</Text>
          {current.bullets.length > 0 && (
            <Card className="gap-2">
              {current.bullets.map((b) => (
                <Text key={b} className="text-body text-text">
                  • {b}
                </Text>
              ))}
            </Card>
          )}
        </View>

        <View className="gap-3">
          <Pressable
            accessibilityRole="button"
            onPress={() => (last ? router.replace("/login") : setStep(step + 1))}
            className="items-center rounded-card bg-primary py-4 active:opacity-80"
          >
            <Text className="text-body font-semibold text-white">
              {last ? "Get started" : "Continue"}
            </Text>
          </Pressable>
          {!last && (
            <Pressable
              accessibilityRole="button"
              onPress={() => router.replace("/login")}
              className="items-center py-2"
            >
              <Text className="text-body text-text-dim">Skip</Text>
            </Pressable>
          )}
        </View>
      </View>
    </SafeAreaView>
  );
}
