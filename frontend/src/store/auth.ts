import { create } from "zustand";

const API_HOST = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const REFRESH_URL = `${API_HOST}/api/v1/auth/refresh`;

interface TokenResponse {
  access_token: string;
  refresh_token: string;
}

interface AuthState {
  isAuthenticated: boolean;
  // Access token kept in memory (not localStorage) for SSE and Authorization headers.
  // The HttpOnly cookie handles browser auto-send for API calls.
  accessToken: string | null;
  login: (accessToken: string) => void;
  logout: () => void;
  initialize: () => void;
  /** Call /auth/refresh to obtain a new access token and store it in memory. */
  refreshAccessToken: () => Promise<string | null>;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  accessToken: null,

  // Called after successful login — tokens are in HttpOnly cookies (auto-sent by browser)
  // accessToken stored in memory only for SSE usage
  login: (accessToken: string) => {
    set({ isAuthenticated: true, accessToken });
  },

  // Called on logout — server clears HttpOnly cookies via /auth/logout
  logout: () => {
    set({ isAuthenticated: false, accessToken: null });
  },

  // Read initial auth state from the non-HttpOnly auth_status cookie.
  // The actual tokens are in HttpOnly cookies (not readable by JS),
  // auth_status=1 is a non-sensitive presence indicator.
  initialize: () => {
    if (typeof window === "undefined") return;
    const isAuthenticated = document.cookie
      .split(";")
      .some((c) => c.trim().startsWith("auth_status=1"));
    set({ isAuthenticated, accessToken: null });
  },

  // Silently refresh the access token using the HttpOnly refresh cookie.
  // Returns the new access token on success, or null on failure.
  refreshAccessToken: async () => {
    try {
      const res = await fetch(REFRESH_URL, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      if (!res.ok) return null;
      const data = (await res.json()) as TokenResponse;
      const token = data.access_token ?? null;
      if (token) {
        set({ isAuthenticated: true, accessToken: token });
      }
      return token;
    } catch {
      return null;
    }
  },
}));
