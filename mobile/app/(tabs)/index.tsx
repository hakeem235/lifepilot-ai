/**
 * Home dashboard — personalized greeting, the gradient AI Daily Brief (real task
 * counts + AI/fallback summary), a tile row (live weather via Open-Meteo and a
 * live commute estimate via Mapbox; meetings/email still sample), quick actions,
 * AI suggestions, and a live preview of today's open tasks. The ＋ Add Task
 * quick action opens natural-language capture (Issue 10.1). Floating AI orb
 * bottom-right.
 */
import { BottomSheetModal } from "@gorhom/bottom-sheet";
import { useUser } from "@clerk/clerk-expo";
import { LinearGradient } from "expo-linear-gradient";
import { router } from "expo-router";
import { useRef } from "react";
import { ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { AiActionMenu } from "../../components/AiActionMenu";
import { CaptureSheet } from "../../components/CaptureSheet";
import {
  AiOrb,
  Badge,
  Chip,
  Fade,
  FadeInUp,
  GlassCard,
  GradientBackdrop,
} from "../../components/ui";
import { useBrief, useCommute, useTasks, useWeather } from "../../lib/hooks";
import { type AiActionId, routeForAction } from "../../lib/aiActions";
import { describeCommute } from "../../lib/traffic";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

// Weather (Open-Meteo) and Traffic (Mapbox, via our backend) are live;
// meetings and email are still labeled sample until wired.
const SAMPLE_TILES = [
  { label: "Meetings", value: "3" },
  { label: "Urgent email", value: "2" },
];

export default function HomeScreen() {
  const { user } = useUser();
  const { brief } = useBrief();
  const { tasks } = useTasks("today");
  const { weather, loading: weatherLoading, error: weatherError } = useWeather();
  const { commute, loading: commuteLoading } = useCommute();
  const commuteTile = describeCommute(commute, commuteLoading);
  const captureRef = useRef<BottomSheetModal>(null);
  const aiMenuRef = useRef<BottomSheetModal>(null);

  const onAiAction = (id: AiActionId) => {
    aiMenuRef.current?.dismiss();
    const route = routeForAction(id);
    if (route) router.push(route);
    else captureRef.current?.present();
  };

  const name = user?.firstName ?? "";

  return (
    <GradientBackdrop>
      <SafeAreaView edges={["top"]} className="flex-1">
        <ScrollView
          contentContainerClassName="px-5 pb-28 pt-2"
          showsVerticalScrollIndicator={false}
        >
          <FadeInUp>
            <Text className="text-display text-text">
              {greeting()}
              {name ? `, ${name}` : ""}
            </Text>
            <Text className="mt-1 text-body text-text-dim">Your Intelligent Daily Companion</Text>
          </FadeInUp>

          {/* AI Daily Brief — gradient hero */}
          <FadeInUp delay={80} className="mt-4">
            <View className="overflow-hidden rounded-card">
              <LinearGradient
                colors={["#4F46E5", "#7C3AED"]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
              >
                <View className="p-5">
                  <View className="flex-row items-center justify-between">
                    <Text className="text-caption font-semibold uppercase tracking-wide text-white/70">
                      AI Daily Brief
                    </Text>
                    {brief && (
                      <View className="rounded-chip bg-white/15 px-2 py-0.5">
                        <Text className="text-caption font-medium text-white">
                          {brief.generated_by === "ai" ? "Claude" : "Auto"}
                        </Text>
                      </View>
                    )}
                  </View>
                  <Text className="mt-3 text-title text-white">
                    {brief ? brief.summary : "Pulling your day together…"}
                  </Text>
                  {brief && (
                    <View className="mt-4 flex-row gap-5">
                      <Stat n={brief.open_tasks} label="Open" />
                      <Stat n={brief.due_today} label="Due today" />
                      <Stat n={brief.high_priority} label="High" />
                    </View>
                  )}
                </View>
              </LinearGradient>
            </View>
          </FadeInUp>

          {/* Context tiles */}
          <FadeInUp delay={140} className="mt-4">
            <View className="flex-row flex-wrap gap-3">
              <GlassCard className="min-w-[46%] flex-1">
                <Text className="text-caption text-text-dim">Weather</Text>
                {weather ? (
                  <>
                    <Text className="mt-1 text-title text-text">
                      {weather.icon} {weather.temperature}°
                    </Text>
                    <Text className="mt-0.5 text-caption text-text-dim" numberOfLines={1}>
                      {weather.description} · {weather.city}
                    </Text>
                  </>
                ) : (
                  <>
                    <Text className="mt-1 text-title text-text-dim">
                      {weatherLoading ? "…" : "—"}
                    </Text>
                    <Text className="mt-0.5 text-caption text-text-dim" numberOfLines={1}>
                      {weatherLoading ? "Loading" : (weatherError ?? "Unavailable")}
                    </Text>
                  </>
                )}
              </GlassCard>
              <GlassCard className="min-w-[46%] flex-1">
                <Text className="text-caption text-text-dim">Traffic</Text>
                <Text
                  className={`mt-1 text-title ${commuteTile.live ? "text-text" : "text-text-dim"}`}
                >
                  {commuteTile.value}
                </Text>
                <Text className="mt-0.5 text-caption text-text-dim" numberOfLines={1}>
                  {commuteTile.detail}
                </Text>
              </GlassCard>
              {SAMPLE_TILES.map((t) => (
                <GlassCard key={t.label} className="min-w-[46%] flex-1">
                  <Text className="text-caption text-text-dim">{t.label}</Text>
                  <Text className="mt-1 text-title text-text">{t.value}</Text>
                  <Text className="mt-0.5 text-caption text-text-dim">sample</Text>
                </GlassCard>
              ))}
            </View>
          </FadeInUp>

          {/* Quick actions */}
          <FadeInUp delay={200} className="mt-5">
            <Text className="mb-2 text-body font-semibold text-text">Quick actions</Text>
            <View className="flex-row flex-wrap gap-2">
              <Chip label="＋ Add Task" onPress={() => captureRef.current?.present()} />
              <Chip label="📝 New Note" />
              <Chip label="🎙 Voice" />
              <Chip label="📷 Scan" />
              <Chip label="⚡ Automate" />
            </View>
          </FadeInUp>

          {/* AI suggestion */}
          <FadeInUp delay={260} className="mt-5">
            <GlassCard>
              <Text className="text-caption font-semibold uppercase text-primary">
                AI suggestion
              </Text>
              <Text className="mt-1 text-body text-text">
                {brief && brief.high_priority > 0
                  ? "Tackle your high-priority task during the 2–4 PM focus window."
                  : "Add a couple of tasks and I'll help you plan the day."}
              </Text>
            </GlassCard>
          </FadeInUp>

          {/* Today's tasks preview */}
          <FadeInUp delay={320} className="mt-5">
            <View className="mb-2 flex-row items-center justify-between">
              <Text className="text-body font-semibold text-text">Today</Text>
              <Text
                onPress={() => router.push("/(tabs)/tasks")}
                className="text-caption text-primary"
              >
                See all
              </Text>
            </View>
            {tasks.length === 0 ? (
              <GlassCard>
                <Text className="text-body text-text-dim">Nothing due today. Enjoy the calm.</Text>
              </GlassCard>
            ) : (
              <View className="gap-2">
                {tasks.slice(0, 3).map((t) => (
                  <Fade key={t.id}>
                    <GlassCard className="flex-row items-center justify-between">
                      <Text className="flex-1 text-body text-text" numberOfLines={1}>
                        {t.title}
                      </Text>
                      <Badge label={t.priority} tone={t.priority as "high" | "medium" | "low"} />
                    </GlassCard>
                  </Fade>
                ))}
              </View>
            )}
          </FadeInUp>
        </ScrollView>

        {/* Floating AI orb — opens the AI action menu */}
        <View className="absolute bottom-24 right-4">
          <AiOrb size={30} onPress={() => aiMenuRef.current?.present()} />
        </View>

        <AiActionMenu ref={aiMenuRef} onSelect={onAiAction} />

        {/* Natural-language capture (Issue 10.1), opened by the ＋ Add Task chip */}
        <CaptureSheet ref={captureRef} />
      </SafeAreaView>
    </GradientBackdrop>
  );
}

function Stat({ n, label }: { n: number; label: string }) {
  return (
    <View>
      <Text className="text-title text-white">{n}</Text>
      <Text className="text-caption text-white/70">{label}</Text>
    </View>
  );
}
