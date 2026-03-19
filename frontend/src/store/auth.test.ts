import { describe, it, expect, beforeEach, vi } from "vitest";
import { useAuthStore } from "./auth";

// Reset Zustand store state between tests
beforeEach(() => {
  useAuthStore.setState({ isAuthenticated: false, accessToken: null });
});

describe("useAuthStore - login", () => {
  it("sets isAuthenticated to true with access token", () => {
    useAuthStore.getState().login("test-access-token");
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(true);
    expect(state.accessToken).toBe("test-access-token");
  });

  it("stores the exact access token string", () => {
    const token = "eyJhbGciOiJIUzI1NiJ9.test.signature";
    useAuthStore.getState().login(token);
    expect(useAuthStore.getState().accessToken).toBe(token);
  });
});

describe("useAuthStore - logout", () => {
  it("clears isAuthenticated and accessToken", () => {
    useAuthStore.getState().login("token-xyz");
    useAuthStore.getState().logout();
    const state = useAuthStore.getState();
    expect(state.isAuthenticated).toBe(false);
    expect(state.accessToken).toBeNull();
  });

  it("is idempotent — calling logout twice works fine", () => {
    useAuthStore.getState().logout();
    useAuthStore.getState().logout();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });
});

describe("useAuthStore - initialize", () => {
  it("sets isAuthenticated=true when auth_status=1 cookie is present", () => {
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "auth_status=1; path=/",
    });
    useAuthStore.getState().initialize();
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    // accessToken stays null — only in-memory via login()
    expect(useAuthStore.getState().accessToken).toBeNull();
  });

  it("sets isAuthenticated=false when auth_status cookie is absent", () => {
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "",
    });
    useAuthStore.getState().initialize();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("sets isAuthenticated=false when auth_status=0", () => {
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "auth_status=0",
    });
    useAuthStore.getState().initialize();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
  });

  it("does not run when window is undefined (SSR)", () => {
    // Simulate SSR: patch window temporarily
    const originalWindow = globalThis.window;
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as any).window = undefined;
    // Should not throw and should not change state
    useAuthStore.getState().initialize();
    // State stays at the beforeEach reset values
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    // Restore
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (globalThis as any).window = originalWindow;
  });
});

describe("useAuthStore - state transitions", () => {
  it("login -> logout -> initialize cycle works correctly", () => {
    Object.defineProperty(document, "cookie", {
      writable: true,
      value: "auth_status=1",
    });
    useAuthStore.getState().login("my-token");
    expect(useAuthStore.getState().isAuthenticated).toBe(true);

    useAuthStore.getState().logout();
    expect(useAuthStore.getState().isAuthenticated).toBe(false);
    expect(useAuthStore.getState().accessToken).toBeNull();

    useAuthStore.getState().initialize();
    expect(useAuthStore.getState().isAuthenticated).toBe(true);
    expect(useAuthStore.getState().accessToken).toBeNull();
  });
});
