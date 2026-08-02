/**
 * ScreenScaffold — shared themed page frame (safe-area + heading) used by the
 * placeholder tab screens. Real screen content replaces the children in Issues
 * 8.2–8.4; the frame demonstrates the token system boots end-to-end.
 */
import { ScrollView, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

export function ScreenScaffold({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children?: React.ReactNode;
}) {
  return (
    <SafeAreaView edges={["top"]} className="flex-1 bg-bg">
      <ScrollView contentContainerClassName="px-5 pb-24 pt-2">
        <Text className="text-display text-text">{title}</Text>
        {subtitle ? <Text className="mt-1 text-body text-text-dim">{subtitle}</Text> : null}
        <View className="mt-4 gap-4">{children}</View>
      </ScrollView>
    </SafeAreaView>
  );
}
