/**
 * Backend API client — attaches the Clerk session JWT as a Bearer token.
 * The backend verifies it against the instance JWKS (users/authentication.py).
 */
import { useAuth } from "@clerk/clerk-expo";

const BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function useApi() {
  const { getToken } = useAuth();

  return async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
    const token = await getToken();
    return fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init.headers ?? {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
  };
}
