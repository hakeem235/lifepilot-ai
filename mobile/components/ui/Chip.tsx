/** Chip — pill for quick actions / filters (prototype chip). */
import { Text, View } from "react-native";

export function Chip({ label, className = "" }: { label: string; className?: string }) {
  return (
    <View className={`rounded-chip bg-primary/10 px-3 py-1.5 ${className}`}>
      <Text className="text-caption font-medium text-primary">{label}</Text>
    </View>
  );
}
