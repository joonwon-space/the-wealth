import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeAll, afterAll } from "vitest";
import { ErrorBoundary, DefaultErrorFallback } from "./ErrorBoundary";

// Suppress expected console.error from ErrorBoundary in tests
beforeAll(() => {
  vi.spyOn(console, "error").mockImplementation(() => {});
});
afterAll(() => {
  vi.restoreAllMocks();
});

function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error("Test error message");
  }
  return <div>Content rendered successfully</div>;
}

describe("ErrorBoundary", () => {
  it("renders children when no error occurs", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={false} />
      </ErrorBoundary>
    );
    expect(screen.getByText("Content rendered successfully")).toBeInTheDocument();
  });

  it("renders default fallback when a child throws", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText("오류가 발생했습니다")).toBeInTheDocument();
    expect(screen.getByText("Test error message")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /다시 시도/i })).toBeInTheDocument();
  });

  it("renders custom fallback when provided", () => {
    const customFallback = (error: Error, reset: () => void) => (
      <div>
        <span>Custom error: {error.message}</span>
        <button onClick={reset}>Reset</button>
      </div>
    );
    render(
      <ErrorBoundary fallback={customFallback}>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText("Custom error: Test error message")).toBeInTheDocument();
  });

  it("shows retry button which triggers reset callback", () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    );
    expect(screen.getByText("오류가 발생했습니다")).toBeInTheDocument();

    const retryButton = screen.getByRole("button", { name: /다시 시도/i });
    // Clicking retry should not throw
    expect(() => fireEvent.click(retryButton)).not.toThrow();
  });
});

describe("DefaultErrorFallback", () => {
  it("renders the error message and retry button", () => {
    const error = new Error("Something went wrong");
    const reset = vi.fn();
    render(<DefaultErrorFallback error={error} reset={reset} />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
    const retryBtn = screen.getByRole("button", { name: /다시 시도/i });
    expect(retryBtn).toBeInTheDocument();
    fireEvent.click(retryBtn);
    expect(reset).toHaveBeenCalledOnce();
  });

  it("shows generic message when error has no message", () => {
    const error = new Error("");
    const reset = vi.fn();
    render(<DefaultErrorFallback error={error} reset={reset} />);
    expect(
      screen.getByText("예기치 않은 오류가 발생했습니다. 잠시 후 다시 시도해주세요.")
    ).toBeInTheDocument();
  });
});
