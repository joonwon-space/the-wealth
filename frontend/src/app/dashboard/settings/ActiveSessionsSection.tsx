"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Laptop, Loader2, LogOut, Shield } from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface SessionItem {
  jti: string;
  created_at: string | null;
  is_current: boolean;
}

function formatSessionDate(isoString: string | null): string {
  if (!isoString) return "날짜 불명";
  const d = new Date(isoString);
  return d.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ActiveSessionsSection(): React.ReactElement {
  const queryClient = useQueryClient();
  const [revokingJti, setRevokingJti] = useState<string | null>(null);

  const {
    data: sessions,
    isLoading,
    isError,
  } = useQuery<SessionItem[]>({
    queryKey: ["auth-sessions"],
    queryFn: () =>
      api.get<SessionItem[]>("/auth/sessions").then((r) => r.data),
    staleTime: 30_000,
  });

  const revokeMutation = useMutation({
    mutationFn: (jti: string) => api.delete(`/auth/sessions/${jti}`),
    onSuccess: (_, jti) => {
      toast.success("세션이 종료되었습니다");
      queryClient.setQueryData<SessionItem[]>(["auth-sessions"], (prev) =>
        prev ? prev.filter((s) => s.jti !== jti) : []
      );
    },
    onError: () => toast.error("세션 종료에 실패했습니다"),
    onSettled: () => setRevokingJti(null),
  });

  const revokeAllMutation = useMutation({
    mutationFn: () => api.post("/auth/logout"),
    onSuccess: () => {
      toast.success("모든 세션이 종료되었습니다. 다시 로그인해주세요.");
      // Redirect after full logout — the interceptor will handle redirect
    },
    onError: () => toast.error("전체 로그아웃에 실패했습니다"),
  });

  const handleRevokeSession = (jti: string) => {
    setRevokingJti(jti);
    revokeMutation.mutate(jti);
  };

  return (
    <Card>
      <CardContent className="space-y-4 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4" aria-hidden="true" />
            <h2 className="text-base font-semibold">활성 세션</h2>
          </div>
          {sessions && sessions.length > 1 && (
            <Button
              variant="outline"
              size="sm"
              className="text-xs text-destructive border-destructive/40 hover:bg-destructive/10"
              onClick={() => revokeAllMutation.mutate()}
              disabled={revokeAllMutation.isPending}
            >
              {revokeAllMutation.isPending && (
                <Loader2 className="mr-1 h-3 w-3 animate-spin" />
              )}
              모든 기기 로그아웃
            </Button>
          )}
        </div>
        <p className="text-sm text-muted-foreground">
          현재 로그인된 기기 목록입니다. 의심스러운 세션은 개별 종료할 수
          있습니다.
        </p>

        {isLoading && (
          <div className="space-y-2">
            {[1, 2].map((i) => (
              <div
                key={i}
                className="h-14 rounded-lg bg-muted animate-pulse"
              />
            ))}
          </div>
        )}

        {isError && (
          <p className="text-sm text-destructive">
            세션 목록을 불러오지 못했습니다.
          </p>
        )}

        {sessions && sessions.length === 0 && (
          <p className="text-sm text-muted-foreground">
            활성 세션이 없습니다.
          </p>
        )}

        {sessions && sessions.length > 0 && (
          <div className="space-y-2">
            {sessions.map((session) => (
              <div
                key={session.jti}
                className="flex items-center justify-between rounded-lg border px-3 py-2.5 text-sm"
              >
                <div className="flex items-center gap-3">
                  <Laptop className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <div>
                    <div className="flex items-center gap-1.5">
                      <span className="font-medium text-xs font-mono">
                        {session.jti.slice(0, 8)}…
                      </span>
                      {session.is_current && (
                        <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-medium text-primary">
                          현재 기기
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      {formatSessionDate(session.created_at)}
                    </p>
                  </div>
                </div>
                {!session.is_current && (
                  <button
                    onClick={() => handleRevokeSession(session.jti)}
                    disabled={revokingJti === session.jti}
                    aria-label="이 세션 종료"
                    className="flex items-center gap-1 rounded border px-2 py-1 text-xs text-muted-foreground hover:text-destructive hover:border-destructive/40 transition-colors disabled:opacity-50"
                  >
                    {revokingJti === session.jti ? (
                      <Loader2 className="h-3 w-3 animate-spin" />
                    ) : (
                      <LogOut className="h-3 w-3" aria-hidden="true" />
                    )}
                    종료
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
