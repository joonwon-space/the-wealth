import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/lib/api", () => ({
  api: { get: vi.fn() },
}));

vi.mock("@/components/ui/input", () => ({
  Input: (props: React.InputHTMLAttributes<HTMLInputElement>) => <input {...props} />,
}));

vi.mock("@/components/ui/dialog", () => ({
  Dialog: ({ children, open }: { children: React.ReactNode; open: boolean }) =>
    open ? <div data-testid="dialog">{children}</div> : null,
  DialogContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogHeader: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  DialogTitle: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
}));

import { StockSearchDialog } from "./StockSearchDialog";

describe("StockSearchDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders when open", () => {
    render(<StockSearchDialog open={true} onClose={() => {}} onSelect={() => {}} />);
    expect(screen.getByTestId("dialog")).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    render(<StockSearchDialog open={false} onClose={() => {}} onSelect={() => {}} />);
    expect(screen.queryByTestId("dialog")).toBeNull();
  });

  it("shows search placeholder text", () => {
    render(<StockSearchDialog open={true} onClose={() => {}} onSelect={() => {}} />);
    expect(screen.getByPlaceholderText(/Search by name or ticker/)).toBeInTheDocument();
  });

  it("shows empty state when no query and no recent", () => {
    render(<StockSearchDialog open={true} onClose={() => {}} onSelect={() => {}} />);
    expect(screen.getByText("Enter a stock name or ticker")).toBeInTheDocument();
  });
});
