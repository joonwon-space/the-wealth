import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: "https://9dcd414aac45d9d356af673e53bf0f63@o4511081209987072.ingest.us.sentry.io/4511081216147456",
  tracesSampleRate: 0.2,
  replaysSessionSampleRate: 0.05,
  replaysOnErrorSampleRate: 1.0,
  integrations: [Sentry.replayIntegration()],
  enabled: process.env.NODE_ENV === "production",
});
