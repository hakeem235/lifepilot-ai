/**
 * Insights — productivity score (animated ring), focus-time + tasks-done stats, an
 * area chart (focus minutes/day) and bar chart (tasks/day), and habit streak — all
 * derived from real Task + UsageEvent data via /api/insights/.
 */
import { ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import {
  AreaChart,
  BarChart,
  FadeInUp,
  GlassCard,
  GradientBackdrop,
  ProgressRing,
} from "../../components/ui";
import { useInsights } from "../../lib/hooks";

export default function InsightsScreen() {
  const { insights, loading } = useInsights();

  return (
    <GradientBackdrop>
      <SafeAreaView edges={["top"]} className="flex-1">
        <ScrollView
          contentContainerClassName="px-5 pb-28 pt-2"
          showsVerticalScrollIndicator={false}
        >
          <Text className="text-display text-text">Insights</Text>

          {loading || !insights ? (
            <Text className="mt-4 text-body text-text-dim">Crunching your week…</Text>
          ) : (
            <>
              {/* Productivity score ring */}
              <FadeInUp delay={60} className="mt-4">
                <GlassCard className="items-center py-6">
                  <Text className="mb-3 text-caption font-semibold uppercase text-text-dim">
                    Weekly productivity
                  </Text>
                  <ProgressRing
                    value={insights.productivity_score}
                    size={140}
                    label={`${insights.productivity_score}`}
                    sublabel="score"
                  />
                </GlassCard>
              </FadeInUp>

              {/* Stats */}
              <FadeInUp delay={120} className="mt-4">
                <View className="flex-row gap-3">
                  <GlassCard className="flex-1">
                    <Text className="text-caption text-text-dim">Tasks done</Text>
                    <Text className="mt-1 text-display text-text">{insights.tasks_completed}</Text>
                  </GlassCard>
                  <GlassCard className="flex-1">
                    <Text className="text-caption text-text-dim">Focus time</Text>
                    <Text className="mt-1 text-display text-text">
                      {Math.round(insights.focus_minutes / 60)}h
                    </Text>
                  </GlassCard>
                </View>
              </FadeInUp>

              {/* Focus area chart */}
              <FadeInUp delay={180} className="mt-4">
                <GlassCard>
                  <Text className="mb-2 text-body font-semibold text-text">Focus this week</Text>
                  <AreaChart data={insights.focus_area.map((d) => d.minutes)} />
                </GlassCard>
              </FadeInUp>

              {/* Tasks bar chart */}
              <FadeInUp delay={240} className="mt-4">
                <GlassCard>
                  <Text className="mb-2 text-body font-semibold text-text">
                    Tasks completed / day
                  </Text>
                  <BarChart data={insights.weekly_tasks.map((d) => d.count)} />
                </GlassCard>
              </FadeInUp>

              {/* Habit streak */}
              <FadeInUp delay={300} className="mt-4">
                <GlassCard className="flex-row items-center justify-between">
                  <View>
                    <Text className="text-caption text-text-dim">Habit streak</Text>
                    <Text className="mt-1 text-title text-text">
                      {insights.habit_streak} day{insights.habit_streak === 1 ? "" : "s"} 🔥
                    </Text>
                  </View>
                  <ProgressRing
                    value={Math.min(100, insights.habit_streak * 10)}
                    size={56}
                    stroke={6}
                  />
                </GlassCard>
              </FadeInUp>
            </>
          )}
        </ScrollView>
      </SafeAreaView>
    </GradientBackdrop>
  );
}
