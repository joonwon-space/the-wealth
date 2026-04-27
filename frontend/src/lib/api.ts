import axios from "axios";
import { toast } from "sonner";
import { useAuthStore } from "@/store/auth";

const API_HOST = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const API_BASE = `${API_HOST}/api/v1`;

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
  // Send HttpOnly cookies on every request
  withCredentials: true,
});

const AUTH_ENDPOINTS = ["/auth/login", "/auth/register", "/auth/refresh"];

/** Extract a human-readable error message from standardized error envelope or legacy format. */
function extractErrorMessage(data: unknown, fallback: string): string {
  if (data && typeof data === "object") {
    const d = data as Record<string, unknown>;
    if (d.error && typeof d.error === "object") {
      const err = d.error as Record<string, unknown>;
      if (typeof err.message === "string") return err.message;
    }
    if (typeof d.detail === "string") return d.detail;
  }
  return fallback;
}

// Single-flight refresh: parallel 401s share one /auth/refresh call instead of
// each issuing their own refresh + redirect.
let refreshInflight: Promise<boolean> | null = null;

function refreshOnce(): Promise<boolean> {
  if (refreshInflight) return refreshInflight;
  refreshInflight = axios
    .post(`${API_BASE}/auth/refresh`, {}, { withCredentials: true })
    .then(() => true)
    .catch(() => false)
    .finally(() => {
      refreshInflight = null;
    });
  return refreshInflight;
}

// Coalesce concurrent redirects to /login into a single navigation.
let redirectingToLogin = false;

function redirectToLogin(): void {
  if (redirectingToLogin) return;
  redirectingToLogin = true;
  // Reset Zustand auth state immediately so any subscribed components stop
  // rendering authenticated UI before the navigation completes.
  useAuthStore.getState().logout();
  // replace() avoids polluting back-history with the failed page.
  // The ?reauth=1 flag tells the middleware to force-clear auth cookies and
  // skip the "logged-in → /dashboard" auto-redirect, preventing a loop on
  // browsers (notably mobile Safari) that don't honor cross-subdomain
  // Set-Cookie deletions reliably.
  window.location.replace("/login?reauth=1");
}

// Auto-refresh on 401 (skip for auth endpoints to let callers handle errors)
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    const isAuthEndpoint = AUTH_ENDPOINTS.some((p) =>
      original?.url?.endsWith(p)
    );

    if (error.response?.status === 401 && !original._retry && !isAuthEndpoint) {
      original._retry = true;
      const ok = await refreshOnce();
      if (ok) {
        return api(original);
      }
      redirectToLogin();
      return Promise.reject(error);
    }
    // Show toast for non-401 errors (auth endpoint 401s are handled by callers)
    if (error.response?.status !== 401) {
      const detail = extractErrorMessage(
        error.response?.data,
        error.message ?? "요청에 실패했습니다"
      );
      toast.error(detail);
    }
    return Promise.reject(error);
  }
);
