/**
 * AI Chat — ChatGPT-style conversation wired to the live AI endpoint (real Claude
 * when a key is set, deterministic fallback otherwise). Typing indicator while the
 * reply is in flight, suggested prompt chips when empty, and voice/file/image input
 * controls (voice/image stubbed for MVP; the text path is fully live).
 *
 * The ＋ button turns whatever is typed into a task (Issue 10.1): the text is
 * parsed server-side into a structured draft, shown here as a preview, and only
 * becomes a real task once the user confirms it (D10).
 */
import { useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  Text,
  TextInput,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { CapturePreviewCard } from "../../components/CapturePreviewCard";
import { TypingDots } from "../../components/TypingDots";
import { UndoBanner } from "../../components/UndoBanner";
import { Fade, GlassCard, GradientBackdrop } from "../../components/ui";
import { useCapture, useChat, useUndo } from "../../lib/hooks";
import type { CaptureDraft } from "../../lib/types";
import { useTheme } from "../../theme/ThemeProvider";

const SUGGESTIONS = [
  "Plan my day",
  "Summarize my emails",
  "Generate a shopping list",
  "What's my priority?",
];
const EMPTY_GREETING =
  "Hi — I'm LifePilot. Ask me to plan your day, prioritize tasks, or summarize what's ahead.";

export default function ChatScreen() {
  const { messages, sending, send } = useChat();
  const { proposal, parsing, saving, parse, confirm, discard } = useCapture();
  const { colors } = useTheme();
  const [text, setText] = useState("");
  // A captured task is reversed by deleting it, so undo carries its id (10.3).
  const { pending: undoOffer, undoing, offer, undo, clear: clearUndo } = useUndo();

  const submit = (value?: string) => {
    const msg = (value ?? text).trim();
    if (!msg || sending) return;
    setText("");
    void send(msg);
  };

  const capture = () => {
    const msg = text.trim();
    if (!msg || parsing) return;
    setText("");
    clearUndo();
    void parse(msg);
  };

  const onConfirm = async (draft: CaptureDraft) => {
    const task = await confirm(draft);
    if (task) offer(`Added “${task.title}”.`, [], [task.id]);
  };

  return (
    <GradientBackdrop>
      <SafeAreaView edges={["top"]} className="flex-1">
        <View className="px-5 pt-2">
          <Text className="text-display text-text">AI Chat</Text>
        </View>

        <KeyboardAvoidingView
          className="flex-1"
          behavior={Platform.OS === "ios" ? "padding" : undefined}
          keyboardVerticalOffset={90}
        >
          <ScrollView
            contentContainerClassName="px-5 pb-4 pt-4 gap-3"
            showsVerticalScrollIndicator={false}
          >
            {messages.length === 0 && !sending && (
              <View className="gap-3">
                <GlassCard>
                  <Text className="text-body text-text">{EMPTY_GREETING}</Text>
                </GlassCard>
                <View className="flex-row flex-wrap gap-2">
                  {SUGGESTIONS.map((s) => (
                    <Pressable
                      key={s}
                      onPress={() => submit(s)}
                      className="rounded-chip border border-primary/30 bg-primary/10 px-3 py-2"
                    >
                      <Text className="text-caption font-medium text-primary">{s}</Text>
                    </Pressable>
                  ))}
                </View>
              </View>
            )}

            {messages.map((m, i) => (
              <Fade key={i}>
                <View className={m.role === "user" ? "items-end" : "items-start"}>
                  <View
                    className={`max-w-[85%] rounded-card px-4 py-3 ${
                      m.role === "user" ? "bg-primary" : "bg-card border border-border/15"
                    }`}
                  >
                    <Text
                      className={m.role === "user" ? "text-body text-white" : "text-body text-text"}
                    >
                      {m.content}
                    </Text>
                  </View>
                </View>
              </Fade>
            ))}

            {sending && (
              <View className="items-start">
                <View className="rounded-card border border-border/15 bg-card px-4 py-2">
                  <TypingDots />
                </View>
              </View>
            )}
          </ScrollView>

          {undoOffer !== null && proposal === null && (
            <UndoBanner
              label={undoOffer.label}
              undoing={undoing}
              onUndo={undo}
              onDismiss={clearUndo}
            />
          )}

          {proposal !== null && (
            <CapturePreviewCard
              proposal={proposal}
              saving={saving}
              onConfirm={onConfirm}
              onDiscard={discard}
            />
          )}

          {/* Input row with voice/file/image controls */}
          <View className="border-t border-border/15 px-4 pb-3 pt-2">
            <View className="flex-row items-center gap-2">
              <Pressable
                accessibilityLabel="Voice input"
                className="h-9 w-9 items-center justify-center rounded-full bg-text-dim/10"
              >
                <Text>🎙</Text>
              </Pressable>
              <Pressable
                accessibilityLabel="Attach image"
                className="h-9 w-9 items-center justify-center rounded-full bg-text-dim/10"
              >
                <Text>📷</Text>
              </Pressable>
              <TextInput
                className="flex-1 rounded-chip border border-border/20 bg-card px-4 py-3 text-body text-text"
                placeholder="Ask LifePilot anything…"
                placeholderTextColor={colors.textDim}
                value={text}
                onChangeText={setText}
                onSubmitEditing={() => submit()}
                returnKeyType="send"
              />
              <Pressable
                accessibilityLabel="Capture as task"
                onPress={capture}
                disabled={!text.trim() || parsing}
                className="h-10 w-10 items-center justify-center rounded-full bg-primary/10 disabled:opacity-40"
              >
                {parsing ? (
                  <ActivityIndicator size="small" color={colors.textDim} />
                ) : (
                  <Text className="text-body font-semibold text-primary">＋</Text>
                )}
              </Pressable>
              <Pressable
                accessibilityLabel="Send"
                onPress={() => submit()}
                disabled={!text.trim() || sending}
                className="h-10 w-10 items-center justify-center rounded-full bg-primary disabled:opacity-40"
              >
                <Text className="text-white">↑</Text>
              </Pressable>
            </View>
          </View>
        </KeyboardAvoidingView>
      </SafeAreaView>
    </GradientBackdrop>
  );
}
