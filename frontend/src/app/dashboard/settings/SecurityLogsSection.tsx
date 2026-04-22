"use client";

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { TableSkeleton } from "@/components/TableSkeleton";

interface SecurityLogEntry {
  id: number;
  action: string;
  ip_address: string | null;
  user_agent: string | null;
  created_at: string;
  meta: Record<string, unknown> | null;
}

const ACTION_LABELS: Record<string, string> = {
  login_success: "로그인 성공",
  login_failure: "로그인 실패",
  logout: "로그아웃",
  password_change: "비밀번호 변경",
  kis_credential_added: "KIS 자격증명 등록",
  kis_credential_deleted: "KIS 자격증명 삭제",
  email_change: "이메일 변경",
  account_deleted: "계정 삭제",
};

function formatAction(action: string): string {
  return ACTION_LABELS[action] ?? action;
}

function formatUA(ua: string | null): string {
  if (!ua) return "—";
  // Truncate long user-agent strings
  return ua.length > 60 ? ua.slice(0, 60) + "…" : ua;
}

export function SecurityLogsSection() {
  const { data: logs, isLoading, isError } = useQuery<SecurityLogEntry[]>({
    queryKey: ["security-logs"],
    queryFn: () => api.get<SecurityLogEntry[]>("/users/me/security-logs").then((r) => r.data),
    staleTime: 30_000,
  });

  if (isLoading) {
    return <TableSkeleton rows={5} columns={4} />;
  }

  if (isError) {
    return (
      <p className="text-sm text-destructive">보안 로그를 불러올 수 없습니다.</p>
    );
  }

  if (!logs || logs.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">보안 이벤트가 없습니다.</p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            {["일시", "이벤트", "IP", "브라우저/기기"].map((h) => (
              <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id} className="border-t hover:bg-muted/20">
              <td className="px-4 py-2 text-xs text-muted-foreground whitespace-nowrap">
                {new Date(log.created_at).toLocaleString("ko-KR")}
              </td>
              <td className="px-4 py-2">
                <span
                  className={`text-xs font-medium ${
                    log.action.includes("failure") || log.action.includes("deleted")
                      ? "text-destructive"
                      : log.action === "login_success"
                      ? "text-primary"
                      : ""
                  }`}
                >
                  {formatAction(log.action)}
                </span>
              </td>
              <td className="px-4 py-2 text-xs font-mono text-muted-foreground">
                {log.ip_address ?? "—"}
              </td>
              <td className="px-4 py-2 text-xs text-muted-foreground max-w-[200px] truncate" title={log.user_agent ?? undefined}>
                {formatUA(log.user_agent)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
