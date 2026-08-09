import "../global.css";

import { ClerkProvider } from "@clerk/clerk-expo";
import { BottomSheetModalProvider } from "@gorhom/bottom-sheet";
import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { GestureHandlerRootView } from "react-native-gesture-handler";

import { tokenCache } from "../lib/tokenCache";
import { ThemeProvider } from "../theme/ThemeProvider";

const publishableKey = process.env.EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY;

if (!publishableKey) {
  throw new Error(
    "Missing EXPO_PUBLIC_CLERK_PUBLISHABLE_KEY — copy mobile/.env.example to .env and fill it in.",
  );
}

export default function RootLayout() {
  return (
    <GestureHandlerRootView style={{ flex: 1 }}>
      <ClerkProvider publishableKey={publishableKey} tokenCache={tokenCache}>
        <ThemeProvider>
          {/*
            Sheets are portalled to this provider so they render ABOVE the tab
            bar. The tab bar is absolutely positioned and is a sibling of every
            screen, so a sheet mounted inside a screen is always painted under
            it — no z-index within the screen can win that.
          */}
          <BottomSheetModalProvider>
            <StatusBar style="auto" />
            <Stack screenOptions={{ headerShown: false, animation: "fade" }}>
              <Stack.Screen name="index" />
              <Stack.Screen name="(auth)" />
              <Stack.Screen name="(tabs)" />
            </Stack>
          </BottomSheetModalProvider>
        </ThemeProvider>
      </ClerkProvider>
    </GestureHandlerRootView>
  );
}
