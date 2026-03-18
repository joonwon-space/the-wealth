import axios from "axios";
import { toast } from "sonner";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
  // Send HttpOnly cookies on every request
  withCredentials: true,
});

const AUTH_ENDPOINTS = ["/auth/login", "/auth/register", "/auth/refresh"];

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
      const detail =
        error.response?.data?.detail ?? error.message ?? "요청에 실패했습니다";
      toast.error(detail);
    }
    return Promise.reject(error);
  }
);
