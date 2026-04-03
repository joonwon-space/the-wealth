"use client";

import { useQuery } from "@tanstack/react-query";
import {
  CheckCircle,
  Key,
  LogIn,
  LogOut,
  Shield,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";

interface SecurityLog {
  id: number;
  action: string;
  ip_address: string | null;
  user_agent: string | null;
  meta: Record<string, unknown> | null;
  created_at: string;
}

interface ActionMeta {
  icon: React.ReactNode;
  label: string;
  color: string;
}

function getActionMeta(action: string): ActionMeta {
  switch (action) {
    case "LOGIN_SUCCESS":
      return {
        icon: <LogIn className="h-3.5 w-3.5" aria-hidden="true" />,
        label: "로그인 성공",
        color: "text-green-600 bg-green-50 dark:bg-green-950",
      };
    case "LOGIN_FAILURE":
      return {
        icon: <XCircle className="h-3.5 w-3.5" aria-hidden="true" />,
        label: "로그인 실패",
        color: "text-destructive bg-destructive/10",
      };
    case "LOGOUT":
      return {
        icon: <LogOut className="h-3.5 w-3.5" aria-hidden="true" />,
        label: "로그아웃",
        color: "text-muted-foreground bg-muted",
      };
    case "PASSWORD_CHANGE":
      return {
        icon: <Key className="h-3.5 w-3.5" aria-hidden="true" />,
        label: "비밀번호 변경",
        color: "text-amber-600 bg-amber-50 dark:bg-amber-950",
      };
    case "KIS_CREDENTIAL_ADDED":
    case "KIS_CREDENTIAL_DELETED":
    case "KIS_CREDENTIAL_UPDATE":
      return {
        icon: <CheckCircle className="h-3.5 w-3.5" aria-hidden="true" />,
        label:
          action === "KIS_CREDENTIAL_ADDED"
            ? "KIS 자격증명 등록"
            : action === "KIS_CREDENTIAL_DELETED"
              ? "KIS 자격증명 삭제"
              : "KIS 자격증명 변경",
        color: "text-blue-600 bg-blue-50 dark:bg-blue-950",
      };
    default:
      return {
        icon: <Shield className="h-3.5 w-3.5" aria-hidden="true" />,
        label: action,
        color: "text-muted-foreground bg-muted",
      };
  }
}

function formatLogDate(isoString: string): string {
  const d = new Date(isoString);
  return d.toLocaleString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function SecurityLogsSection(): React.ReactElement {
  const {
    data: logs,
    isLoading,
    isError,
  } = useQuery<SecurityLog[]>({
    queryKey: ["security-logs"],
    queryFn: () =>
      api
        .get<SecurityLog[]>("/users/me/security-logs")
        .then((r) => r.data),
    staleTime: 60_000,
  });

  return (
    <Card>
      <CardContent className="space-y-4 p-6">
        <div className="flex items-center gap-2">
          <Shield className="h-4 w-4" aria-hidden="true" />
          <h2 className="text-base font-semibold">보안 로그</h2>
        </div>
        <p className="text-sm text-muted-foreground">
          최근 50건의 계정 보안 이벤트 내역입니다.
        </p>

        {isLoading && (
          <div className="space-y-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-12 rounded-lg bg-muted animate-pulse"
              />
            ))}
          </div>
        )}

        {isError && (
          <p className="text-sm text-destructive">
            보안 로그를 불러오지 못했습니다.
          </p>
        )}

        {logs && logs.length === 0 && (
          <p className="text-sm text-muted-foreground">
            기록된 보안 이벤트가 없습니다.
          </p>
        )}

        {logs && logs.length > 0 && (
          <div className="space-y-1.5">
            {logs.map((log) => {
              const meta = getActionMeta(log.action);
              return (
                <div
                  key={log.id}
                  className="flex items-start gap-3 rounded-lg border px-3 py-2.5 text-sm"
                >
                  <span
                    className={`mt-0.5 flex items-center gap-1 rounded px-1.5 py-0.5 text-xs font-medium shrink-0 ${meta.color}`}
                  >
                    {meta.icon}
                    {meta.label}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="truncate text-xs text-muted-foreground">
                        {log.ip_address ?? "IP 불명"}
                      </span>
                      <span className="shrink-0 text-xs text-muted-foreground tabular-nums">
                        {formatLogDate(log.created_at)}
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
