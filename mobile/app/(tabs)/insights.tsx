/** Insights (placeholder shell) — real productivity metrics/streaks in Issue 8.4. */
import { Text, View } from "react-native";

import { ScreenScaffold } from "../../components/ScreenScaffold";
import { Card, Ring } from "../../components/ui";

export default function InsightsScreen() {
  return (
    <ScreenScaffold title="Insights" subtitle="Derived from real activity in Issue 8.4">
      <Card className="flex-row items-center justify-between">
        <View>
          <Text className="text-caption text-text-dim">Habit streak</Text>
          <Text className="text-title text-text">12 days</Text>
        </View>
        <Ring value={80} label="80%" />
      </Card>
    </ScreenScaffold>
  );
}
