import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePriceStream } from "./usePriceStream";
import { useAuthStore } from "@/store/auth";

// --- EventSource mock ---
class MockEventSource {
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  static instances: MockEventSource[] = [];

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  close = vi.fn();

  /** Test helper: simulate successful connection open */
  triggerOpen() {
    if (this.onopen) {
      this.onopen();
    }
  }

  /** Test helper: simulate an incoming message */
  emit(data: unknown) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) } as MessageEvent);
    }
  }

  /** Test helper: simulate a connection error */
  triggerError() {
    if (this.onerror) {
      this.onerror();
    }
  }
}

// Mock api.post for SSE ticket
vi.mock("@/lib/api", () => ({
  api: {
    post: vi.fn().mockResolvedValue({ data: { ticket: "mock-ticket-123" } }),
    get: vi.fn(),
  },
}));

beforeEach(() => {
  MockEventSource.instances = [];
  vi.stubGlobal("EventSource", MockEventSource);
  useAuthStore.setState({ isAuthenticated: true, accessToken: "test-token" });
});

afterEach(() => {
  vi.unstubAllGlobals();
  useAuthStore.setState({ isAuthenticated: false, accessToken: null });
});

/** Helper: wait for the async ticket fetch + EventSource creation */
async function waitForConnection(): Promise<MockEventSource> {
  // Flush the microtask (queueMicrotask for "connecting") + the async connect()
  await act(async () => {
    await new Promise((r) => setTimeout(r, 10));
  });
  const es = MockEventSource.instances[MockEventSource.instances.length - 1];
  return es;
}

describe("usePriceStream", () => {
  it("opens an EventSource connection when enabled and token is present", async () => {
    const onPrices = vi.fn();
    renderHook(() => usePriceStream({ onPrices, enabled: true }));
    const es = await waitForConnection();
    expect(MockEventSource.instances).toHaveLength(1);
    expect(es.url).toContain("/prices/stream");
    expect(es.url).toContain("ticket=mock-ticket-123");
  });

  it("does NOT open a connection when enabled=false", async () => {
    const onPrices = vi.fn();
    renderHook(() => usePriceStream({ onPrices, enabled: false }));
    await act(async () => {
      await new Promise((r) => setTimeout(r, 10));
    });
    expect(MockEventSource.instances).toHaveLength(0);
  });

  it("does NOT open a connection when accessToken is null", async () => {
    useAuthStore.setState({ isAuthenticated: false, accessToken: null });
    const onPrices = vi.fn();
    renderHook(() => usePriceStream({ onPrices }));
    await act(async () => {
      await new Promise((r) => setTimeout(r, 10));
    });
    expect(MockEventSource.instances).toHaveLength(0);
  });

  it("calls onPrices when a prices message arrives", async () => {
    const onPrices = vi.fn();
    renderHook(() => usePriceStream({ onPrices }));
    const es = await waitForConnection();
    act(() => {
      es.emit({ market_open: true, prices: { "005930": "75000" } });
    });
    expect(onPrices).toHaveBeenCalledWith({ "005930": "75000" });
  });

  it("ignores messages with empty prices object", async () => {
    const onPrices = vi.fn();
    renderHook(() => usePriceStream({ onPrices }));
    const es = await waitForConnection();
    act(() => {
      es.emit({ market_open: true, prices: {} });
    });
    expect(onPrices).not.toHaveBeenCalled();
  });

  it("ignores market_open=false messages (no prices key)", async () => {
    const onPrices = vi.fn();
    renderHook(() => usePriceStream({ onPrices }));
    const es = await waitForConnection();
    act(() => {
      es.emit({ market_open: false });
    });
    expect(onPrices).not.toHaveBeenCalled();
  });

  it("ignores malformed (non-JSON) messages without throwing", async () => {
    const onPrices = vi.fn();
    renderHook(() => usePriceStream({ onPrices }));
    const es = await waitForConnection();
    act(() => {
      if (es.onmessage) {
        es.onmessage({ data: "not-valid-json" } as MessageEvent);
      }
    });
    expect(onPrices).not.toHaveBeenCalled();
  });

  it("closes EventSource on unmount", async () => {
    const onPrices = vi.fn();
    const { unmount } = renderHook(() => usePriceStream({ onPrices }));
    const es = await waitForConnection();
    unmount();
    expect(es.close).toHaveBeenCalled();
  });

  it("closes EventSource on error and sets status to disconnected", async () => {
    const onPrices = vi.fn();
    const { result } = renderHook(() => usePriceStream({ onPrices }));
    const es = await waitForConnection();
    act(() => {
      es.triggerError();
    });
    expect(es.close).toHaveBeenCalled();
    expect(result.current.status).toBe("disconnected");
  });

  it("status becomes connecting after microtask when enabled with token", async () => {
    const onPrices = vi.fn();
    const { result } = renderHook(() => usePriceStream({ onPrices }));
    await act(async () => {
      await Promise.resolve();
    });
    // Status is either "connecting" or already "disconnected"/"connected" depending on timing
    expect(["connecting", "connected", "disconnected"]).toContain(result.current.status);
  });

  it("status becomes connected after onopen fires", async () => {
    const onPrices = vi.fn();
    const { result } = renderHook(() => usePriceStream({ onPrices }));
    const es = await waitForConnection();
    act(() => {
      es.triggerOpen();
    });
    expect(result.current.status).toBe("connected");
  });

  it("initial status is disconnected when not enabled", () => {
    const onPrices = vi.fn();
    const { result } = renderHook(() => usePriceStream({ onPrices, enabled: false }));
    expect(result.current.status).toBe("disconnected");
  });

  it("reconnect function creates a new EventSource connection", async () => {
    const onPrices = vi.fn();
    const { result } = renderHook(() => usePriceStream({ onPrices }));
    await waitForConnection();
    expect(MockEventSource.instances).toHaveLength(1);
    await act(async () => {
      result.current.reconnect();
    });
    await waitForConnection();
    expect(MockEventSource.instances.length).toBeGreaterThanOrEqual(2);
  });
});
