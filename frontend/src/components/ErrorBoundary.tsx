"use client";

import { Component, ErrorInfo, ReactNode } from "react";
import * as Sentry from "@sentry/nextjs";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  children: ReactNode;
  /** Optional custom fallback UI. Receives error and a reset callback. */
  fallback?: (error: Error, reset: () => void) => ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * React Error Boundary for catching client-side rendering errors.
 * Renders a default fallback UI with an error message and a Retry button,
 * or a custom fallback if provided via the `fallback` prop.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    Sentry.captureException(error, { extra: { componentStack: info.componentStack } });
    if (process.env.NODE_ENV !== "production") {
      console.error("[ErrorBoundary] Caught error:", error, info.componentStack);
    }
  }

  private readonly handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError && this.state.error) {
      if (this.props.fallback) {
        return this.props.fallback(this.state.error, this.handleReset);
      }
      return (
        <DefaultErrorFallback
          error={this.state.error}
          reset={this.handleReset}
        />
      );
    }
    return this.props.children;
  }
}

interface FallbackProps {
  error: Error;
  reset: () => void;
}

export function DefaultErrorFallback({ error, reset }: FallbackProps): ReactNode {
  return (
    <div
      role="alert"
      className="flex flex-col items-center justify-center rounded-lg border border-destructive/20 bg-destructive/5 px-6 py-12 text-center"
    >
      <AlertTriangle className="mb-3 h-10 w-10 text-destructive/60" />
      <h2 className="text-lg font-semibold">오류가 발생했습니다</h2>
      <p className="mt-1 max-w-md text-sm text-muted-foreground">
        {error.message || "예기치 않은 오류가 발생했습니다. 잠시 후 다시 시도해주세요."}
      </p>
      <Button onClick={reset} variant="outline" className="mt-5 gap-2">
        <RefreshCw className="h-4 w-4" />
        다시 시도
      </Button>
    </div>
  );
}
