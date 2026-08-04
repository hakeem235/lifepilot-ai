/**
 * NotificationsSheet — the in-app notification center (Issue 9.4). Lists alerts
 * created by the backend scheduled job, shows read/unread state, and lets the
 * user mark one or all as read (clearing the badge).
 */
import BottomSheet, { BottomSheetBackdrop, BottomSheetScrollView } from "@gorhom/bottom-sheet";
import { forwardRef, useCallback } from "react";
import { Pressable, Text, View } from "react-native";

import type { AppNotification } from "../lib/types";
import { useTheme } from "../theme/ThemeProvider";

export const NotificationsSheet = forwardRef<
  BottomSheet,
  {
    notifications: AppNotification[];
    onMarkRead: (id: string) => void;
    onMarkAllRead: () => void;
  }
>(function NotificationsSheet({ notifications, onMarkRead, onMarkAllRead }, ref) {
  const { colors } = useTheme();

  const renderBackdrop = useCallback(
    (props: React.ComponentProps<typeof BottomSheetBackdrop>) => (
      <BottomSheetBackdrop {...props} disappearsOnIndex={-1} appearsOnIndex={0} />
    ),
    [],
  );

  return (
    <BottomSheet
      ref={ref}
      index={-1}
      snapPoints={["55%"]}
      enablePanDownToClose
      backdropComponent={renderBackdrop}
      backgroundStyle={{ backgroundColor: colors.card }}
      handleIndicatorStyle={{ backgroundColor: colors.textDim }}
    >
      <BottomSheetScrollView contentContainerStyle={{ padding: 20, gap: 10 }}>
        <View className="flex-row items-center justify-between">
          <Text className="text-title text-text">Notifications</Text>
          {notifications.some((n) => !n.read) && (
            <Pressable onPress={onMarkAllRead} className="active:opacity-70">
              <Text className="text-caption font-semibold text-primary">Mark all read</Text>
            </Pressable>
          )}
        </View>

        {notifications.length === 0 ? (
          <Text className="text-caption text-text-dim">You&apos;re all caught up.</Text>
        ) : (
          notifications.map((n) => (
            <Pressable
              key={n.id}
              onPress={() => !n.read && onMarkRead(n.id)}
              className={`rounded-card border p-3 active:opacity-80 ${
                n.read ? "border-border/20 bg-bg" : "border-primary/30 bg-primary/5"
              }`}
            >
              <View className="flex-row items-center gap-2">
                {!n.read && <View className="h-2 w-2 rounded-full bg-primary" />}
                <Text className="flex-1 text-body font-semibold text-text" numberOfLines={1}>
                  {n.title}
                </Text>
              </View>
              <Text className="mt-0.5 text-caption text-text-dim" numberOfLines={2}>
                {n.body}
              </Text>
            </Pressable>
          ))
        )}
      </BottomSheetScrollView>
    </BottomSheet>
  );
});
