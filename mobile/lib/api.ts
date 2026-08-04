/**
 * Backend API client — attaches the Clerk session JWT as a Bearer token.
 * The backend verifies it against the instance JWKS (users/authentication.py).
 */
import { useAuth } from "@clerk/clerk-expo";
import { useCallback, useRef } from "react";

const BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function useApi() {
  const { getToken } = useAuth();

  // Keep the latest getToken in a ref and return a permanently stable apiFetch
  // (empty deps). Clerk's getToken identity changes across renders, so depending
  // on it would still hand out a new apiFetch each render — which invalidates every
  // dependent useCallback/useEffect in hooks.ts and drives an infinite refetch loop
  // ("Maximum update depth exceeded"). The ref sidesteps that entirely.
  const getTokenRef = useRef(getToken);
  getTokenRef.current = getToken;

  return useCallback(async function apiFetch(
    path: string,
    init: RequestInit = {},
  ): Promise<Response> {
    const token = await getTokenRef.current();
    return fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init.headers ?? {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
    });
  }, []);
}
