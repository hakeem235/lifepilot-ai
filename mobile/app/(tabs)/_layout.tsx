/**
 * App shell — 5-tab bottom navigation (Home · Tasks · Planner · Insights ·
 * Profile) behind the biometric gate. The AI Chat tab was removed; its
 * natural-language capture (Issue 10.1) now opens from the home screen. The tab bar is a translucent glass surface
 * floating over each screen's ambient gradient.
 */
import { useAuth } from "@clerk/clerk-expo";
import { BlurView } from "expo-blur";
import { Redirect, Tabs } from "expo-router";
import { Text, type ColorValue } from "react-native";

import { BiometricGate } from "../../components/BiometricGate";
import { brand } from "../../theme/tokens";
import { useTheme } from "../../theme/ThemeProvider";

function TabIcon({ glyph, color }: { glyph: string; color: ColorValue }) {
  return <Text style={{ color, fontSize: 18 }}>{glyph}</Text>;
}

export default function TabsLayout() {
  const { colors, name } = useTheme();
  const { isLoaded, isSignedIn } = useAuth();

  if (isLoaded && !isSignedIn) {
    return <Redirect href="/onboarding" />;
  }

  return (
    <BiometricGate>
      <Tabs
        screenOptions={{
          headerShown: false,
          tabBarActiveTintColor: brand.primary,
          tabBarInactiveTintColor: colors.textDim,
          sceneStyle: { backgroundColor: "transparent" },
          tabBarBackground: () => (
            <BlurView
              intensity={50}
              tint={name === "dark" ? "dark" : "light"}
              style={{ position: "absolute", inset: 0 }}
            />
          ),
          tabBarStyle: {
            position: "absolute",
            backgroundColor: name === "dark" ? "rgba(30,41,59,0.6)" : "rgba(255,255,255,0.7)",
            borderTopColor: colors.border,
          },
        }}
      >
        <Tabs.Screen
          name="index"
          options={{
            title: "Home",
            tabBarIcon: ({ color }) => <TabIcon glyph="⌂" color={color} />,
          }}
        />
        <Tabs.Screen
          name="tasks"
          options={{
            title: "Tasks",
            tabBarIcon: ({ color }) => <TabIcon glyph="✓" color={color} />,
          }}
        />
        <Tabs.Screen
          name="planner"
          options={{
            title: "Planner",
            tabBarIcon: ({ color }) => <TabIcon glyph="◷" color={color} />,
          }}
        />
        <Tabs.Screen
          name="insights"
          options={{
            title: "Insights",
            tabBarIcon: ({ color }) => <TabIcon glyph="▤" color={color} />,
          }}
        />
        <Tabs.Screen
          name="profile"
          options={{
            title: "Profile",
            tabBarIcon: ({ color }) => <TabIcon glyph="◍" color={color} />,
          }}
        />
      </Tabs>
    </BiometricGate>
  );
}
