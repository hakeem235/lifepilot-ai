/**
 * Profile (placeholder shell) — identity, dark-mode toggle, settings rows land in
 * Issue 8.4. The dark-mode toggle already works against ThemeProvider to prove
 * the theme system end-to-end.
 */
import { Switch, Text } from "react-native";

import { ScreenScaffold } from "../../components/ScreenScaffold";
import { Card } from "../../components/ui";
import { useTheme } from "../../theme/ThemeProvider";

export default function ProfileScreen() {
  const { name, toggle } = useTheme();
  return (
    <ScreenScaffold title="Profile" subtitle="Settings & personalization in Issue 8.4">
      <Card className="flex-row items-center justify-between">
        <Text className="text-body font-semibold text-text">Dark mode</Text>
        <Switch value={name === "dark"} onValueChange={toggle} />
      </Card>
    </ScreenScaffold>
  );
}
