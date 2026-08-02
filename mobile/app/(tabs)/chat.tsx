/** AI Chat (placeholder shell) — real Claude conversation in Issue 8.3. */
import { Text, View } from "react-native";

import { ScreenScaffold } from "../../components/ScreenScaffold";
import { Card, Chip } from "../../components/ui";

export default function ChatScreen() {
  return (
    <ScreenScaffold title="AI Chat" subtitle="Grounded in your tasks — wired in Issue 8.3">
      <View className="flex-row flex-wrap gap-2">
        <Chip label="Summarize my emails" />
        <Chip label="Plan my day" />
        <Chip label="Shopping list" />
      </View>
      <Card>
        <Text className="text-body text-text-dim">Ask LifePilot anything…</Text>
      </Card>
    </ScreenScaffold>
  );
}
