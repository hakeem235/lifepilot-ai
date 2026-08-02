/** Card — rounded surface container (prototype card). Composes from tokens. */
import { View, type ViewProps } from "react-native";

export function Card({ className = "", ...props }: ViewProps & { className?: string }) {
  return (
    <View
      className={`rounded-card bg-card border border-border/10 p-4 ${className}`}
      {...props}
    />
  );
}
