import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock dependencies
vi.mock("@/lib/api", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock("sonner", () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

vi.mock("next/link", () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock("lucide-react", () => ({
  Eye: () => <span data-testid="eye-icon" />,
  ExternalLink: () => <span data-testid="external-link-icon" />,
  Plus: () => <span data-testid="plus-icon" />,
  Trash2: () => <span data-testid="trash-icon" />,
}));

vi.mock("@/components/StockSearchDialog", () => ({
  StockSearchDialog: ({
    open,
    onClose,
    onSelect,
  }: {
    open: boolean;
    onClose: () => void;
    onSelect: (ticker: string, name: string) => void;
  }) =>
    open ? (
      <div data-testid="stock-search-dialog">
        <button onClick={onClose}>Close</button>
        <button onClick={() => onSelect("005930", "삼성전자")}>Select Samsung</button>
      </div>
    ) : null,
}));

vi.mock("@/components/ui/button", () => ({
  Button: ({
    children,
    onClick,
  }: {
    children: React.ReactNode;
    onClick?: () => void;
  }) => <button onClick={onClick}>{children}</button>,
}));

vi.mock("@/components/ui/skeleton", () => ({
  Skeleton: ({ className }: { className?: string }) => (
    <div data-testid="skeleton" className={className} />
  ),
}));

import { WatchlistSection } from "./WatchlistSection";
import { api } from "@/lib/api";
import { toast } from "sonner";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

describe("WatchlistSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows skeleton while loading", () => {
    // api.get never resolves during this test
    mockApi.get.mockReturnValue(new Promise(() => {}));
    render(<WatchlistSection />);
    expect(screen.getAllByTestId("skeleton").length).toBeGreaterThan(0);
  });

  it("shows empty state when watchlist is empty", async () => {
    mockApi.get.mockResolvedValue({ data: [] });
    render(<WatchlistSection />);
    await waitFor(() => {
      expect(screen.getByText(/관심 종목을 추가하면/)).toBeInTheDocument();
    });
  });

  it("renders watchlist items when data is loaded", async () => {
    mockApi.get.mockResolvedValue({
      data: [
        { id: 1, ticker: "005930", name: "삼성전자", market: "KRX" },
        { id: 2, ticker: "000660", name: "SK하이닉스", market: "KRX" },
      ],
    });
    render(<WatchlistSection />);
    await waitFor(() => {
      expect(screen.getByText("삼성전자")).toBeInTheDocument();
      expect(screen.getByText("SK하이닉스")).toBeInTheDocument();
    });
  });

  it("displays ticker and market badge for each item", async () => {
    mockApi.get.mockResolvedValue({
      data: [{ id: 1, ticker: "005930", name: "삼성전자", market: "KRX" }],
    });
    render(<WatchlistSection />);
    await waitFor(() => {
      expect(screen.getByText("005930")).toBeInTheDocument();
      expect(screen.getByText("KRX")).toBeInTheDocument();
    });
  });

  it("opens StockSearchDialog when add button is clicked", async () => {
    mockApi.get.mockResolvedValue({ data: [] });
    render(<WatchlistSection />);
    await waitFor(() => {
      expect(screen.queryByTestId("stock-search-dialog")).toBeNull();
    });
    fireEvent.click(screen.getByText("추가"));
    expect(screen.getByTestId("stock-search-dialog")).toBeInTheDocument();
  });

  it("closes StockSearchDialog when onClose is called", async () => {
    mockApi.get.mockResolvedValue({ data: [] });
    render(<WatchlistSection />);
    await waitFor(() => {});

    fireEvent.click(screen.getByText("추가"));
    expect(screen.getByTestId("stock-search-dialog")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Close"));
    expect(screen.queryByTestId("stock-search-dialog")).toBeNull();
  });

  it("adds item to list on successful add", async () => {
    mockApi.get.mockResolvedValue({ data: [] });
    mockApi.post.mockResolvedValue({
      data: { id: 3, ticker: "005930", name: "삼성전자", market: "KRX" },
    });

    render(<WatchlistSection />);
    await waitFor(() => {
      expect(screen.getByText(/관심 종목을 추가하면/)).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("추가"));
    fireEvent.click(screen.getByText("Select Samsung"));

    await waitFor(() => {
      expect(screen.getByText("삼성전자")).toBeInTheDocument();
    });
    expect(toast.success).toHaveBeenCalled();
  });

  it("shows error toast on add failure", async () => {
    mockApi.get.mockResolvedValue({ data: [] });
    mockApi.post.mockRejectedValue(new Error("Network error"));

    render(<WatchlistSection />);
    await waitFor(() => {});

    fireEvent.click(screen.getByText("추가"));
    fireEvent.click(screen.getByText("Select Samsung"));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalled();
    });
  });

  it("shows conflict error toast when item already added (409)", async () => {
    mockApi.get.mockResolvedValue({ data: [] });
    const error = { response: { status: 409 } };
    mockApi.post.mockRejectedValue(error);

    render(<WatchlistSection />);
    await waitFor(() => {});

    fireEvent.click(screen.getByText("추가"));
    fireEvent.click(screen.getByText("Select Samsung"));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("이미 추가된 종목입니다");
    });
  });

  it("removes item from list on delete", async () => {
    mockApi.get.mockResolvedValue({
      data: [{ id: 1, ticker: "005930", name: "삼성전자", market: "KRX" }],
    });
    mockApi.delete.mockResolvedValue({});

    render(<WatchlistSection />);
    await waitFor(() => {
      expect(screen.getByText("삼성전자")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTitle("관심 종목 삭제"));

    await waitFor(() => {
      expect(screen.queryByText("삼성전자")).toBeNull();
    });
    expect(toast.success).toHaveBeenCalled();
  });

  it("shows error toast when delete fails", async () => {
    mockApi.get.mockResolvedValue({
      data: [{ id: 1, ticker: "005930", name: "삼성전자", market: "KRX" }],
    });
    mockApi.delete.mockRejectedValue(new Error("Delete failed"));

    render(<WatchlistSection />);
    await waitFor(() => {
      expect(screen.getByText("삼성전자")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTitle("관심 종목 삭제"));

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith("삭제 실패");
    });
  });

  it("shows section heading", async () => {
    mockApi.get.mockResolvedValue({ data: [] });
    render(<WatchlistSection />);
    await waitFor(() => {
      expect(screen.getByText("관심 종목")).toBeInTheDocument();
    });
  });

  it("shows ticker as label when name is empty", async () => {
    mockApi.get.mockResolvedValue({
      data: [{ id: 1, ticker: "AAPL", name: "", market: "NYSE" }],
    });
    render(<WatchlistSection />);
    await waitFor(() => {
      // When name is empty, component shows ticker as the main label
      const tickers = screen.getAllByText("AAPL");
      expect(tickers.length).toBeGreaterThanOrEqual(1);
    });
  });
});
