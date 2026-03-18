import { create } from "zustand";

interface AuthState {
  isAuthenticated: boolean;
  // Access token kept in memory (not localStorage) for SSE and Authorization headers.
  // The HttpOnly cookie handles browser auto-send for API calls.
  accessToken: string | null;
  login: (accessToken: string) => void;
  logout: () => void;
  initialize: () => void;
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
}));
