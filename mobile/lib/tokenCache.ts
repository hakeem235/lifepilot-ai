/**
 * Clerk token cache backed by expo-secure-store (Issue 8.1).
 * Session tokens live in the iOS keychain / Android keystore — never AsyncStorage.
 */
import * as SecureStore from "expo-secure-store";

import type { TokenCache } from "@clerk/clerk-expo";

export const tokenCache: TokenCache = {
  async getToken(key: string) {
    try {
      return await SecureStore.getItemAsync(key);
    } catch {
      // A corrupt entry would otherwise wedge sign-in forever — clear it.
      await SecureStore.deleteItemAsync(key).catch(() => {});
      return null;
    }
  },
  async saveToken(key: string, value: string) {
    try {
      await SecureStore.setItemAsync(key, value);
    } catch {
      // Non-fatal: Clerk falls back to in-memory for this session.
    }
  },
  async clearToken(key: string) {
    await SecureStore.deleteItemAsync(key).catch(() => {});
  },
};
