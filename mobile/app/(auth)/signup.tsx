/** Sign-up — email + password with email-code verification (Clerk default). */
import { useSignUp } from "@clerk/clerk-expo";
import { Link, router } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

export default function SignupScreen() {
  const { signUp, setActive, isLoaded } = useSignUp();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onCreate = useCallback(async () => {
    if (!isLoaded || busy) return;
    setBusy(true);
    setError(null);
    try {
      await signUp.create({ emailAddress: email, password });
      await signUp.prepareEmailAddressVerification({ strategy: "email_code" });
      setVerifying(true);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Sign-up failed. Try again.");
    } finally {
      setBusy(false);
    }
  }, [busy, email, isLoaded, password, signUp]);

  const onVerify = useCallback(async () => {
    if (!isLoaded || busy) return;
    setBusy(true);
    setError(null);
    try {
      const attempt = await signUp.attemptEmailAddressVerification({ code });
      if (attempt.status === "complete") {
        await setActive({ session: attempt.createdSessionId });
        router.replace("/");
      } else {
        setError("Verification incomplete — check the code and try again.");
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Invalid code. Try again.");
    } finally {
      setBusy(false);
    }
  }, [busy, code, isLoaded, setActive, signUp]);

  return (
    <SafeAreaView className="flex-1 bg-bg">
      <View className="flex-1 justify-center gap-6 px-6">
        <View className="gap-1">
          <Text className="text-display text-text">
            {verifying ? "Check your email" : "Create your account"}
          </Text>
          <Text className="text-body text-text-dim">
            {verifying ? `We sent a code to ${email}.` : "One account for your whole day."}
          </Text>
        </View>

        {verifying ? (
          <View className="gap-3">
            <TextInput
              className="rounded-card border border-border/20 bg-card px-4 py-4 text-center text-title text-text"
              placeholder="123456"
              keyboardType="number-pad"
              maxLength={6}
              value={code}
              onChangeText={setCode}
            />
            {error ? <Text className="text-caption text-danger">{error}</Text> : null}
            <Pressable
              accessibilityRole="button"
              disabled={busy}
              onPress={onVerify}
              className="items-center rounded-card bg-primary py-4 active:opacity-80 disabled:opacity-50"
            >
              <Text className="text-body font-semibold text-white">
                {busy ? "Verifying…" : "Verify"}
              </Text>
            </Pressable>
          </View>
        ) : (
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
              placeholder="Password (8+ characters)"
              secureTextEntry
              autoComplete="new-password"
              value={password}
              onChangeText={setPassword}
            />
            {error ? <Text className="text-caption text-danger">{error}</Text> : null}
            <Pressable
              accessibilityRole="button"
              disabled={busy}
              onPress={onCreate}
              className="items-center rounded-card bg-primary py-4 active:opacity-80 disabled:opacity-50"
            >
              <Text className="text-body font-semibold text-white">
                {busy ? "Creating…" : "Create account"}
              </Text>
            </Pressable>
          </View>
        )}

        <View className="flex-row justify-center gap-1">
          <Text className="text-body text-text-dim">Already have an account?</Text>
          <Link href="/login" className="text-body font-semibold text-primary">
            Sign in
          </Link>
        </View>
      </View>
    </SafeAreaView>
  );
}
