"use client";

import { useEffect } from "react";
import * as Sentry from "@sentry/nextjs";

export function SentryInit() {
  useEffect(() => {
    if (process.env.NODE_ENV === "production" && process.env.NEXT_PUBLIC_SENTRY_DSN) {
      Sentry.init({
        dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
        tracesSampleRate: 0.2,
        replaysSessionSampleRate: 0.05,
        replaysOnErrorSampleRate: 1.0,
        integrations: [Sentry.replayIntegration()],
      });
    }
  }, []);

  return null;
}
