"use client";

import { useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { usePullToRefresh } from "@/hooks/usePullToRefresh";
import { PullToRefreshIndicator } from "@/components/PullToRefreshIndicator";
import { useIsMobile } from "@/hooks/useMediaQuery";

/**
 * Mounted at the dashboard layout level. On mobile viewports it attaches a
 * pull-to-refresh gesture to the document body that invalidates all active
 * React Query cache entries. Desktop: no-op.
 */
export function MobilePullToRefresh() {
  const queryClient = useQueryClient();
  const isMobile = useIsMobile();

  const refresh = useCallback(async () => {
    await queryClient.invalidateQueries({ type: "active" });
    // Small grace delay so the indicator is visible to the user even on fast
    // mutations; without it the spinner barely flashes.
    await new Promise((resolve) => setTimeout(resolve, 250));
  }, [queryClient]);

  const { state } = usePullToRefresh({
    onRefresh: refresh,
    disabled: !isMobile,
  });

  return (
    <PullToRefreshIndicator
      distance={state.distance}
      threshold={state.threshold}
      armed={state.armed}
      refreshing={state.refreshing}
    />
  );
}
