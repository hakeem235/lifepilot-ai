/**
 * Profile — identity + dark-mode toggle + sign out (Issue 8.1); full settings
 * rows land in Issue 8.4.
 */
import { useAuth, useUser } from "@clerk/clerk-expo";
import { Pressable, Switch, Text } from "react-native";

import { ScreenScaffold } from "../../components/ScreenScaffold";
import { Card } from "../../components/ui";
import { useTheme } from "../../theme/ThemeProvider";

export default function ProfileScreen() {
  const { name, toggle } = useTheme();
  const { signOut } = useAuth();
  const { user } = useUser();

  return (
    <ScreenScaffold
      title="Profile"
      subtitle={
        user?.primaryEmailAddress?.emailAddress ?? "Settings & personalization in Issue 8.4"
      }
    >
      <Card className="flex-row items-center justify-between">
        <Text className="text-body font-semibold text-text">Dark mode</Text>
        <Switch value={name === "dark"} onValueChange={toggle} />
      </Card>
      <Pressable
        accessibilityRole="button"
        onPress={() => void signOut()}
        className="items-center rounded-card border border-danger/30 py-4 active:opacity-80"
      >
        <Text className="text-body font-semibold text-danger">Sign out</Text>
      </Pressable>
    </ScreenScaffold>
  );
}
