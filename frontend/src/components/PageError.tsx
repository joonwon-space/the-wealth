"use client";

import { AlertTriangle, RefreshCw } from "lucide-react";

interface PageErrorProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
}

/**
 * Standardized full-page error state component.
 * Use when a page fails to load its primary data.
 */
export function PageError({
  title = "데이터를 불러올 수 없습니다",
  message = "서버에 연결할 수 없습니다",
  onRetry,
}: PageErrorProps) {
  return (
    <div className="flex flex-col items-center justify-center rounded-xl border border-destructive/30 bg-destructive/5 py-16 text-center">
      <AlertTriangle className="mb-3 h-10 w-10 text-destructive/60" />
      <p className="text-lg font-semibold">{title}</p>
      <p className="mt-1 text-sm text-muted-foreground">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-5 flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          <RefreshCw className="h-4 w-4" />
          다시 시도
        </button>
      )}
    </div>
  );
}
