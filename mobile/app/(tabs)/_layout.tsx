/**
 * App shell — 5-tab bottom navigation (PRD §4: Home · Tasks · AI Chat · Insights ·
 * Profile). Tab bar is themed from tokens. Screen content is real in Issues
 * 8.2–8.4; here each tab is a themed placeholder so the shell boots end-to-end.
 */
import { useAuth } from "@clerk/clerk-expo";
import { Redirect, Tabs } from "expo-router";
import { Text, type ColorValue } from "react-native";

import { BiometricGate } from "../../components/BiometricGate";
import { brand } from "../../theme/tokens";
import { useTheme } from "../../theme/ThemeProvider";

function TabIcon({ glyph, color }: { glyph: string; color: ColorValue }) {
  return <Text style={{ color, fontSize: 18 }}>{glyph}</Text>;
}

export default function TabsLayout() {
  const { colors } = useTheme();
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
          tabBarStyle: {
            backgroundColor: colors.card,
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
          name="chat"
          options={{
            title: "AI Chat",
            tabBarIcon: ({ color }) => <TabIcon glyph="✦" color={color} />,
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
