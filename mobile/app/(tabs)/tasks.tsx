/** Tasks (placeholder shell) — real CRUD + Today/Upcoming/Completed in Issue 8.2. */
import { Text, View } from "react-native";

import { ScreenScaffold } from "../../components/ScreenScaffold";
import { Badge, Card, ProgressBar } from "../../components/ui";

export default function TasksScreen() {
  return (
    <ScreenScaffold title="Tasks" subtitle="Real create/complete/track lands in Issue 8.2">
      <Card>
        <View className="flex-row items-center justify-between">
          <Text className="text-body font-semibold text-text">Sample task</Text>
          <Badge label="High" tone="high" />
        </View>
        <View className="mt-3">
          <ProgressBar value={40} />
        </View>
      </Card>
    </ScreenScaffold>
  );
}
