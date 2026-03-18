import axios from "axios";
import { toast } from "sonner";

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
      try {
        // HttpOnly refresh token cookie is sent automatically
        await axios.post(
          `${API_BASE}/auth/refresh`,
          {},
          { withCredentials: true }
        );
        return api(original);
      } catch {
        window.location.href = "/login";
      }
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
