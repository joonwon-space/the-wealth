"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { TableSkeleton } from "@/components/TableSkeleton";
import { Loader2, Monitor } from "lucide-react";
import { toast } from "sonner";

interface SessionInfo {
  jti: string;
  created_at: string;
}

export function ActiveSessionsSection() {
  const queryClient = useQueryClient();
  const [revokingJti, setRevokingJti] = useState<string | null>(null);

  const { data: sessions, isLoading, isError } = useQuery<SessionInfo[]>({
    queryKey: ["auth-sessions"],
    queryFn: () => api.get<SessionInfo[]>("/auth/sessions").then((r) => r.data),
    staleTime: 30_000,
  });

  const revokeMutation = useMutation({
    mutationFn: (jti: string) => api.delete(`/auth/sessions/${jti}`),
    onMutate: (jti) => setRevokingJti(jti),
    onSuccess: (_, jti) => {
      queryClient.setQueryData<SessionInfo[]>(["auth-sessions"], (prev) =>
        prev ? prev.filter((s) => s.jti !== jti) : []
      );
      toast.success("세션이 취소되었습니다");
    },
    onError: () => {
      toast.error("세션 취소에 실패했습니다");
    },
    onSettled: () => setRevokingJti(null),
  });

  if (isLoading) {
    return <TableSkeleton rows={3} columns={3} />;
  }

  if (isError) {
    return (
      <p className="text-sm text-destructive">세션 정보를 불러올 수 없습니다.</p>
    );
  }

  if (!sessions || sessions.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">활성 세션이 없습니다.</p>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs text-muted-foreground">
        총 {sessions.length}개의 활성 세션이 있습니다. 의심스러운 세션을 개별 취소할 수 있습니다.
      </p>
      <div className="divide-y rounded-lg border">
        {sessions.map((s) => (
          <div key={s.jti} className="flex items-center justify-between px-4 py-3">
            <div className="flex items-center gap-3">
              <Monitor className="h-4 w-4 text-muted-foreground shrink-0" />
              <div>
                <p className="text-sm font-medium font-mono">{s.jti.slice(0, 8)}…</p>
                <p className="text-xs text-muted-foreground">
                  {s.created_at
                    ? `생성: ${new Date(s.created_at).toLocaleString("ko-KR")}`
                    : "생성 시간 알 수 없음"}
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => revokeMutation.mutate(s.jti)}
              disabled={revokingJti === s.jti}
              className="text-xs text-destructive border-destructive/40 hover:bg-destructive/10"
            >
              {revokingJti === s.jti ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                "취소"
              )}
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}
