"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";

export interface Notification {
  id: number;
  user_id: number;
  type: string;
  title: string;
  body: string | null;
  is_read: boolean;
  created_at: string;
}

const QUERY_KEY = ["notifications"] as const;

async function fetchNotifications(): Promise<Notification[]> {
  const res = await api.get<Notification[]>("/notifications");
  return res.data;
}

async function markOneRead(notificationId: number): Promise<Notification> {
  const res = await api.patch<Notification>(
    `/notifications/${notificationId}/read`
  );
  return res.data;
}

async function markAllRead(): Promise<void> {
  await api.post("/notifications/read-all");
}

/** TanStack Query hook for the notifications list and mutations. */
export function useNotifications() {
  const queryClient = useQueryClient();

  const query = useQuery<Notification[]>({
    queryKey: QUERY_KEY,
    queryFn: fetchNotifications,
    refetchInterval: 60_000, // Poll every 60s for new notifications
    staleTime: 30_000,
  });

  const markReadMutation = useMutation({
    mutationFn: markOneRead,
    onMutate: async (notificationId: number) => {
      await queryClient.cancelQueries({ queryKey: QUERY_KEY });
      const previous = queryClient.getQueryData<Notification[]>(QUERY_KEY);
      // Optimistic update: mark as read locally
      queryClient.setQueryData<Notification[]>(QUERY_KEY, (old) =>
        old?.map((n) =>
          n.id === notificationId ? { ...n, is_read: true } : n
        ) ?? []
      );
      return { previous };
    },
    onError: (_err, _id, context) => {
      if (context?.previous) {
        queryClient.setQueryData(QUERY_KEY, context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });

  const markAllReadMutation = useMutation({
    mutationFn: markAllRead,
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: QUERY_KEY });
      const previous = queryClient.getQueryData<Notification[]>(QUERY_KEY);
      // Optimistic update: mark all as read locally
      queryClient.setQueryData<Notification[]>(QUERY_KEY, (old) =>
        old?.map((n) => ({ ...n, is_read: true })) ?? []
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(QUERY_KEY, context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: QUERY_KEY });
    },
  });

  const notifications = query.data ?? [];
  const unreadCount = notifications.filter((n) => !n.is_read).length;

  return {
    notifications,
    unreadCount,
    isLoading: query.isLoading,
    markRead: markReadMutation.mutate,
    markAllRead: markAllReadMutation.mutate,
  };
}
