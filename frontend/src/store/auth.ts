import { create } from "zustand";

interface AuthState {
  isAuthenticated: boolean;
  accessToken: string | null;
  login: (accessToken: string, refreshToken: string) => void;
  logout: () => void;
  initialize: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  isAuthenticated: false,
  accessToken: null,

  initialize: () => {
    if (typeof window === "undefined") return;
    const token = localStorage.getItem("access_token");
    set({ isAuthenticated: !!token, accessToken: token });
  },

  login: (accessToken, refreshToken) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("access_token", accessToken);
      localStorage.setItem("refresh_token", refreshToken);
    }
    set({ isAuthenticated: true, accessToken });
  },

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    }
    set({ isAuthenticated: false, accessToken: null });
  },
}));
