import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { usePriceStream } from "./usePriceStream";
import { useAuthStore } from "@/store/auth";

// --- EventSource mock ---
class MockEventSource {
  url: string;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  static instances: MockEventSource[] = [];

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  close = vi.fn();

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

beforeEach(() => {
  MockEventSource.instances = [];
  vi.stubGlobal("EventSource", MockEventSource);
  // Reset auth store and inject a token so hook is enabled by default
  useAuthStore.setState({ isAuthenticated: true, accessToken: "test-token" });
});

afterEach(() => {
  vi.unstubAllGlobals();
  useAuthStore.setState({ isAuthenticated: false, accessToken: null });
});

describe("usePriceStream", () => {
  it("opens an EventSource connection when enabled and token is present", () => {
    const onPrices = vi.fn();
    renderHook(() => usePriceStream({ onPrices, enabled: true }));
    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toContain("/prices/stream");
    expect(MockEventSource.instances[0].url).toContain("token=test-token");
  });

  it("does NOT open a connection when enabled=false", () => {
    const onPrices = vi.fn();
    renderHook(() => usePriceStream({ onPrices, enabled: false }));
    expect(MockEventSource.instances).toHaveLength(0);
  });

  it("does NOT open a connection when accessToken is null", () => {
    useAuthStore.setState({ isAuthenticated: false, accessToken: null });
    const onPrices = vi.fn();
    renderHook(() => usePriceStream({ onPrices }));
    expect(MockEventSource.instances).toHaveLength(0);
  });

  it("calls onPrices when a prices message arrives", () => {
    const onPrices = vi.fn();
    renderHook(() => usePriceStream({ onPrices }));
    const es = MockEventSource.instances[0];
    act(() => {
      es.emit({ market_open: true, prices: { "005930": "75000" } });
    });
    expect(onPrices).toHaveBeenCalledWith({ "005930": "75000" });
  });

  it("ignores messages with empty prices object", () => {
    const onPrices = vi.fn();
    renderHook(() => usePriceStream({ onPrices }));
    const es = MockEventSource.instances[0];
    act(() => {
      es.emit({ market_open: true, prices: {} });
    });
    expect(onPrices).not.toHaveBeenCalled();
  });

  it("ignores market_open=false messages (no prices key)", () => {
    const onPrices = vi.fn();
    renderHook(() => usePriceStream({ onPrices }));
    const es = MockEventSource.instances[0];
    act(() => {
      es.emit({ market_open: false });
    });
    expect(onPrices).not.toHaveBeenCalled();
  });

  it("ignores malformed (non-JSON) messages without throwing", () => {
    const onPrices = vi.fn();
    renderHook(() => usePriceStream({ onPrices }));
    const es = MockEventSource.instances[0];
    act(() => {
      if (es.onmessage) {
        es.onmessage({ data: "not-valid-json" } as MessageEvent);
      }
    });
    expect(onPrices).not.toHaveBeenCalled();
  });

  it("closes EventSource on unmount", () => {
    const onPrices = vi.fn();
    const { unmount } = renderHook(() => usePriceStream({ onPrices }));
    const es = MockEventSource.instances[0];
    unmount();
    expect(es.close).toHaveBeenCalled();
  });

  it("closes EventSource on error and nulls the ref", () => {
    const onPrices = vi.fn();
    renderHook(() => usePriceStream({ onPrices }));
    const es = MockEventSource.instances[0];
    act(() => {
      es.triggerError();
    });
    expect(es.close).toHaveBeenCalled();
  });
});
