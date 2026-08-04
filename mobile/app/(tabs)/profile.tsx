/**
 * Profile — identity, connected accounts, preferences (dark mode + notification/AI
 * toggles), and sign out. Dark mode drives ThemeProvider live; connected accounts
 * are labeled previews until the P2 OAuth integrations land.
 */
import { useAuth, useUser } from "@clerk/clerk-expo";
import { LinearGradient } from "expo-linear-gradient";
import { useState } from "react";
import { Pressable, ScrollView, Switch, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { FadeInUp, GlassCard, GradientBackdrop } from "../../components/ui";
import { useTheme } from "../../theme/ThemeProvider";

const ACCOUNTS = [
  { name: "Google", status: "Connected", on: true },
  { name: "Microsoft", status: "Not connected", on: false },
  { name: "Apple", status: "Not connected", on: false },
];

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <View className="flex-row items-center justify-between py-3">
      <Text className="text-body text-text">{label}</Text>
      {children}
    </View>
  );
}

export default function ProfileScreen() {
  const { name, toggle } = useTheme();
  const { signOut } = useAuth();
  const { user } = useUser();
  const [notifications, setNotifications] = useState(true);
  const [proactiveAI, setProactiveAI] = useState(true);

  const email = user?.primaryEmailAddress?.emailAddress ?? "";
  const initial = (user?.firstName ?? email ?? "?").slice(0, 1).toUpperCase();

  return (
    <GradientBackdrop>
      <SafeAreaView edges={["top"]} className="flex-1">
        <ScrollView
          contentContainerClassName="px-5 pb-28 pt-2"
          showsVerticalScrollIndicator={false}
        >
          <Text className="text-display text-text">Profile</Text>

          {/* Identity */}
          <FadeInUp delay={60} className="mt-4">
            <GlassCard className="flex-row items-center gap-4">
              <LinearGradient
                colors={["#4F46E5", "#7C3AED"]}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
                style={{
                  width: 56,
                  height: 56,
                  borderRadius: 28,
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Text className="text-title text-white">{initial}</Text>
              </LinearGradient>
              <View className="flex-1">
                <Text className="text-body font-semibold text-text">
                  {user?.fullName || "LifePilot user"}
                </Text>
                <Text className="text-caption text-text-dim" numberOfLines={1}>
                  {email}
                </Text>
              </View>
            </GlassCard>
          </FadeInUp>

          {/* Connected accounts */}
          <FadeInUp delay={120} className="mt-4">
            <Text className="mb-2 text-caption font-semibold uppercase text-text-dim">
              Connected accounts
            </Text>
            <GlassCard>
              {ACCOUNTS.map((a, i) => (
                <View
                  key={a.name}
                  className={`flex-row items-center justify-between py-3 ${i > 0 ? "border-t border-border/10" : ""}`}
                >
                  <Text className="text-body text-text">{a.name}</Text>
                  <Text className={`text-caption ${a.on ? "text-success" : "text-text-dim"}`}>
                    {a.status}
                  </Text>
                </View>
              ))}
            </GlassCard>
          </FadeInUp>

          {/* Preferences */}
          <FadeInUp delay={180} className="mt-4">
            <Text className="mb-2 text-caption font-semibold uppercase text-text-dim">
              Preferences
            </Text>
            <GlassCard>
              <Row label="Dark mode">
                <Switch
                  testID="toggle-dark-mode"
                  accessibilityLabel="Dark mode toggle"
                  value={name === "dark"}
                  onValueChange={toggle}
                />
              </Row>
              <View className="border-t border-border/10" />
              <Row label="Notifications">
                <Switch value={notifications} onValueChange={setNotifications} />
              </Row>
              <View className="border-t border-border/10" />
              <Row label="Proactive AI nudges">
                <Switch value={proactiveAI} onValueChange={setProactiveAI} />
              </Row>
            </GlassCard>
          </FadeInUp>

          {/* Subscription (visible, not wired — D6) */}
          <FadeInUp delay={240} className="mt-4">
            <GlassCard className="flex-row items-center justify-between">
              <View>
                <Text className="text-body font-semibold text-text">LifePilot Free</Text>
                <Text className="text-caption text-text-dim">Upgrade coming soon</Text>
              </View>
              <View className="rounded-chip bg-primary/10 px-3 py-1">
                <Text className="text-caption font-semibold text-primary">Free</Text>
              </View>
            </GlassCard>
          </FadeInUp>

          <FadeInUp delay={300} className="mt-4">
            <Pressable
              accessibilityRole="button"
              onPress={() => void signOut()}
              className="items-center rounded-card border border-danger/30 py-4 active:opacity-80"
            >
              <Text className="text-body font-semibold text-danger">Sign out</Text>
            </Pressable>
          </FadeInUp>
        </ScrollView>
      </SafeAreaView>
    </GradientBackdrop>
  );
}
