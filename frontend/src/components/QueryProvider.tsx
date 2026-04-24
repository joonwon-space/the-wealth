"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { persistQueryClient } from "@tanstack/query-persist-client-core";
import { createSyncStoragePersister } from "@tanstack/query-sync-storage-persister";
import { useEffect, useState } from "react";

interface QueryProviderProps {
  children: React.ReactNode;
}

// Queries whose last snapshot is safe to display while offline.
const PERSIST_QUERY_PREFIXES = [
  "portfolios",
  "portfolios-with-prices",
  "holdings",
  "analytics",
] as const;

export function QueryProvider({ children }: QueryProviderProps) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 1,
            gcTime: 1000 * 60 * 60 * 24,
          },
        },
      }),
  );

  useEffect(() => {
    if (typeof window === "undefined") return;

    const persister = createSyncStoragePersister({
      storage: window.localStorage,
      key: "wealth-query-cache",
      throttleTime: 1000,
    });

    const [unsubscribe] = persistQueryClient({
      queryClient,
      persister,
      maxAge: 1000 * 60 * 60 * 24,
      dehydrateOptions: {
        shouldDehydrateQuery: (query) => {
          const key = Array.isArray(query.queryKey)
            ? String(query.queryKey[0])
            : "";
          return PERSIST_QUERY_PREFIXES.some((prefix) => key.startsWith(prefix));
        },
      },
    });

    return () => {
      if (typeof unsubscribe === "function") unsubscribe();
    };
  }, [queryClient]);

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
