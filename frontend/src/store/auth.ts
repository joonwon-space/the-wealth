import { create } from "zustand";

const COOKIE_OPTS = "path=/; SameSite=Lax; max-age=1800"; // 30분 (access token 수명)
const REFRESH_COOKIE_OPTS = "path=/; SameSite=Lax; max-age=604800"; // 7일

function setCookie(name: string, value: string, opts: string) {
  document.cookie = `${name}=${value}; ${opts}`;
}

function deleteCookie(name: string) {
  document.cookie = `${name}=; path=/; max-age=0`;
}

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
      setCookie("access_token", accessToken, COOKIE_OPTS);
      setCookie("refresh_token", refreshToken, REFRESH_COOKIE_OPTS);
    }
    set({ isAuthenticated: true, accessToken });
  },

  logout: () => {
    if (typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
      deleteCookie("access_token");
      deleteCookie("refresh_token");
    }
    set({ isAuthenticated: false, accessToken: null });
  },
}));
