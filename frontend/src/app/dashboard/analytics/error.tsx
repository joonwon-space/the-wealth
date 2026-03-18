"use client";

import { DefaultErrorFallback } from "@/components/ErrorBoundary";

interface Props {
  error: Error;
  reset: () => void;
}

export default function AnalyticsError({ error, reset }: Props) {
  return <DefaultErrorFallback error={error} reset={reset} />;
}
