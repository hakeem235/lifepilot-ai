/**
 * BiometricGate — Face ID / Touch ID unlock after cold start (Issue 8.1).
 * Runs once per app launch for signed-in users. Devices without biometrics
 * enrolled (simulator, Expo Go) pass through — Clerk's session is still the
 * auth boundary; this is a local privacy lock, not the security perimeter.
 */
import * as LocalAuthentication from "expo-local-authentication";
import { useCallback, useEffect, useState } from "react";
import { Pressable, Text, View } from "react-native";

type GateState = "checking" | "locked" | "unlocked";

export function BiometricGate({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<GateState>("checking");

  const attemptUnlock = useCallback(async () => {
    const hasHardware = await LocalAuthentication.hasHardwareAsync();
    const enrolled = await LocalAuthentication.isEnrolledAsync();
    if (!hasHardware || !enrolled) {
      setState("unlocked"); // no biometrics available — pass through
      return;
    }
    const result = await LocalAuthentication.authenticateAsync({
      promptMessage: "Unlock LifePilot",
    });
    setState(result.success ? "unlocked" : "locked");
  }, []);

  useEffect(() => {
    void attemptUnlock();
  }, [attemptUnlock]);

  if (state === "unlocked") return <>{children}</>;

  return (
    <View className="flex-1 items-center justify-center gap-4 bg-bg px-6">
      <Text className="text-display text-text">🔒</Text>
      <Text className="text-title text-text">LifePilot is locked</Text>
      {state === "locked" && (
        <Pressable
          accessibilityRole="button"
          onPress={attemptUnlock}
          className="items-center rounded-card bg-primary px-8 py-4 active:opacity-80"
        >
          <Text className="text-body font-semibold text-white">Unlock</Text>
        </Pressable>
      )}
    </View>
  );
}
