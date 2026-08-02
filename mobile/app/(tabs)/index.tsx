/**
 * Home (placeholder shell) — AI Summary hero + stat cards + quick actions become
 * real in Issue 8.3. This screen showcases the design tokens/components so the
 * shell boots end-to-end.
 */
import { Text, View } from "react-native";

import { ScreenScaffold } from "../../components/ScreenScaffold";
import { Card, Chip, Fab } from "../../components/ui";

export default function HomeScreen() {
  return (
    <>
      <ScreenScaffold title="Good day" subtitle="Your Intelligent Daily Companion">
        <Card className="bg-primary">
          <Text className="text-caption font-semibold uppercase text-white/70">
            AI Summary · preview
          </Text>
          <Text className="mt-2 text-title text-white">
            Your day at a glance will appear here.
          </Text>
          <Text className="mt-1 text-body text-white/80">
            Wired to real tasks in Issue 8.3.
          </Text>
        </Card>
        <View className="flex-row flex-wrap gap-2">
          <Chip label="Add Task" />
          <Chip label="New Note" />
          <Chip label="Voice" />
          <Chip label="Scan Doc" />
        </View>
      </ScreenScaffold>
      <Fab label="🎙" accessibilityLabel="Voice capture" />
    </>
  );
}
