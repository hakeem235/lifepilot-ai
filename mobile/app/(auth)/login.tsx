/**
 * Login — Apple / Google / Microsoft SSO + email/password (PRD §4.2, D2).
 * SSO uses Clerk's SSO flow (dev instance ships shared OAuth credentials).
 * Sign-up with email-code verification lives in signup.tsx.
 */
import { useSignIn, useSSO } from "@clerk/clerk-expo";
import { Link, router } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { useCallback, useEffect, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

WebBrowser.maybeCompleteAuthSession();

type Strategy = "oauth_apple" | "oauth_google" | "oauth_microsoft";

const SSO_BUTTONS: { strategy: Strategy; label: string }[] = [
  { strategy: "oauth_apple", label: " Continue with Apple" },
  { strategy: "oauth_google", label: "Continue with Google" },
  { strategy: "oauth_microsoft", label: "Continue with Microsoft" },
];

export default function LoginScreen() {
  const { startSSOFlow } = useSSO();
  const { signIn, setActive, isLoaded } = useSignIn();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    // Warm the browser for a snappier OAuth handoff on Android; harmless on iOS.
    void WebBrowser.warmUpAsync();
    return () => {
      void WebBrowser.coolDownAsync();
    };
  }, []);

  const onSSO = useCallback(
    async (strategy: Strategy) => {
      setError(null);
      try {
        const { createdSessionId, setActive: ssoSetActive } = await startSSOFlow({ strategy });
        if (createdSessionId && ssoSetActive) {
          await ssoSetActive({ session: createdSessionId });
          router.replace("/");
        }
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : "Sign-in failed. Try again.");
      }
    },
    [startSSOFlow],
  );

  const onEmailSignIn = useCallback(async () => {
    if (!isLoaded || busy) return;
    setBusy(true);
    setError(null);
    try {
      const attempt = await signIn.create({ identifier: email, password });
      if (attempt.status === "complete") {
        await setActive({ session: attempt.createdSessionId });
        router.replace("/");
      } else {
        setError("Additional verification required — finish signing in on the web.");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Sign-in failed. Check your credentials.");
    } finally {
      setBusy(false);
    }
  }, [busy, email, isLoaded, password, setActive, signIn]);

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <View className="flex-1 justify-center gap-6 px-6">
        <View className="gap-1">
          <Text className="text-display text-text">Welcome to LifePilot</Text>
          <Text className="text-body text-text-dim">Your Intelligent Daily Companion</Text>
        </View>

        <View className="gap-3">
          {SSO_BUTTONS.map(({ strategy, label }) => (
            <Pressable
              key={strategy}
              accessibilityRole="button"
              onPress={() => onSSO(strategy)}
              className="items-center rounded-card border border-border/20 bg-card py-4 active:opacity-80"
            >
              <Text className="text-body font-semibold text-text">{label}</Text>
            </Pressable>
          ))}
        </View>

        <View className="flex-row items-center gap-3">
          <View className="h-px flex-1 bg-border/20" />
          <Text className="text-caption text-text-dim">or with email</Text>
          <View className="h-px flex-1 bg-border/20" />
        </View>

        <View className="gap-3">
          <TextInput
            className="rounded-card border border-border/20 bg-card px-4 py-4 text-body text-text"
            placeholder="Email"
            autoCapitalize="none"
            autoComplete="email"
            keyboardType="email-address"
            value={email}
            onChangeText={setEmail}
          />
          <TextInput
            className="rounded-card border border-border/20 bg-card px-4 py-4 text-body text-text"
            placeholder="Password"
            secureTextEntry
            autoComplete="current-password"
            value={password}
            onChangeText={setPassword}
          />
          {error ? <Text className="text-caption text-danger">{error}</Text> : null}
          <Pressable
            accessibilityRole="button"
            disabled={busy}
            onPress={onEmailSignIn}
            className="items-center rounded-card bg-primary py-4 active:opacity-80 disabled:opacity-50"
          >
            <Text className="text-body font-semibold text-white">
              {busy ? "Signing in…" : "Sign in"}
            </Text>
          </Pressable>
        </View>

        <View className="flex-row justify-center gap-1">
          <Text className="text-body text-text-dim">New here?</Text>
          <Link href="/signup" className="text-body font-semibold text-primary">
            Create an account
          </Link>
        </View>
      </View>
    </SafeAreaView>
  );
}
