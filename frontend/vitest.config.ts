import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    // Tests use absolute URLs (`http://localhost:8000/...`) for MSW handlers.
    // Production resolves NEXT_PUBLIC_API_URL to empty so axios uses
    // same-origin `/api/v1` (proxied by Next rewrites), but in jsdom the
    // origin is `http://localhost:3000`, which wouldn't match the handlers.
    // Override here so tests keep their existing absolute-URL setup.
    env: {
      NEXT_PUBLIC_API_URL: "http://localhost:8000",
    },
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
});
