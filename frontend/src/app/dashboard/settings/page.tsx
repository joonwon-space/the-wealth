"use client";

import { useEffect, useState } from "react";
import { RefreshCw, CheckCircle, XCircle } from "lucide-react";
import { api } from "@/lib/api";

interface SyncLog {
  id: number;
  portfolio_id: number;
  status: string;
  inserted: number;
  updated: number;
  deleted: number;
  message: string;
  synced_at: string;
}

interface Portfolio {
  id: number;
  name: string;
}

export default function SettingsPage() {
  const [appKey, setAppKey] = useState("");
  const [appSecret, setAppSecret] = useState("");
  const [accountNo, setAccountNo] = useState("");
  const [credSaving, setCredSaving] = useState(false);
  const [credSuccess, setCredSuccess] = useState(false);

  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState<string>("");
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<string | null>(null);

  const [logs, setLogs] = useState<SyncLog[]>([]);
  const [logsLoading, setLogsLoading] = useState(true);

  useEffect(() => {
    api.get<Portfolio[]>("/portfolios").then(({ data }) => {
      setPortfolios(data);
      if (data.length > 0) setSelectedPortfolio(String(data[0].id));
    });
    api.get<SyncLog[]>("/sync/logs")
      .then(({ data }) => setLogs(data))
      .finally(() => setLogsLoading(false));
  }, []);

  const handleCredSave = async (e: React.FormEvent) => {
    e.preventDefault();
    setCredSaving(true);
    setCredSuccess(false);
    try {
      await api.post("/users/kis-credentials", {
        app_key: appKey,
        app_secret: appSecret,
        account_no: accountNo || undefined,
      });
      setCredSuccess(true);
      setAppKey("");
      setAppSecret("");
      setAccountNo("");
    } finally {
      setCredSaving(false);
    }
  };

  const handleSync = async () => {
    if (!selectedPortfolio) return;
    setSyncing(true);
    setSyncResult(null);
    try {
      const { data } = await api.post<{ status: string; inserted: number; updated: number; deleted: number }>(
        `/sync/${selectedPortfolio}`,
        null,
        { params: { account_no: accountNo || undefined } }
      );
      setSyncResult(`동기화 완료 — 추가 ${data.inserted}건 / 수정 ${data.updated}건 / 삭제 ${data.deleted}건`);
      // 로그 새로고침
      const { data: newLogs } = await api.get<SyncLog[]>("/sync/logs");
      setLogs(newLogs);
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null;
      setSyncResult(`오류: ${msg ?? "동기화 실패"}`);
    } finally {
      setSyncing(false);
    }
  };

  return (
    <div className="space-y-8 max-w-xl">
      <h1 className="text-2xl font-bold">설정</h1>

      {/* KIS 자격증명 */}
      <section className="space-y-4 rounded-xl border bg-card p-6 shadow-sm">
        <h2 className="text-base font-semibold">KIS OpenAPI 자격증명</h2>
        <p className="text-sm text-muted-foreground">
          한국투자증권 OpenAPI 앱키와 시크릿을 입력하세요. AES-256으로 암호화하여 저장됩니다.
        </p>
        <form onSubmit={handleCredSave} className="space-y-3">
          <div className="space-y-1">
            <label className="text-sm font-medium">앱키 (App Key)</label>
            <input
              type="text"
              value={appKey}
              onChange={(e) => setAppKey(e.target.value)}
              placeholder="PS7yzJ..."
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring font-mono"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">앱시크릿 (App Secret)</label>
            <input
              type="password"
              value={appSecret}
              onChange={(e) => setAppSecret(e.target.value)}
              placeholder="••••••••"
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
            />
          </div>
          <div className="space-y-1">
            <label className="text-sm font-medium">계좌번호 (선택)</label>
            <input
              type="text"
              value={accountNo}
              onChange={(e) => setAccountNo(e.target.value)}
              placeholder="63853538"
              className="w-full rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring font-mono"
            />
          </div>
          <div className="flex items-center gap-3">
            <button
              type="submit"
              disabled={credSaving || !appKey || !appSecret}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
            >
              {credSaving ? "저장 중..." : "저장"}
            </button>
            {credSuccess && (
              <span className="flex items-center gap-1 text-sm text-green-600">
                <CheckCircle className="h-4 w-4" /> 저장되었습니다
              </span>
            )}
          </div>
        </form>
      </section>

      {/* 계좌 동기화 */}
      <section className="space-y-4 rounded-xl border bg-card p-6 shadow-sm">
        <h2 className="text-base font-semibold">계좌 수동 동기화</h2>
        <p className="text-sm text-muted-foreground">
          KIS 실계좌 잔고를 조회해서 DB holdings와 동기화합니다.
        </p>
        <div className="flex items-center gap-3">
          <select
            value={selectedPortfolio}
            onChange={(e) => setSelectedPortfolio(e.target.value)}
            className="rounded-lg border bg-background px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-ring"
          >
            {portfolios.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <button
            onClick={handleSync}
            disabled={syncing || !selectedPortfolio}
            className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:opacity-90 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "동기화 중..." : "지금 동기화"}
          </button>
        </div>
        {syncResult && (
          <p className={`text-sm ${syncResult.startsWith("오류") ? "text-destructive" : "text-green-600"}`}>
            {syncResult}
          </p>
        )}
      </section>

      {/* 동기화 이력 */}
      <section className="space-y-3">
        <h2 className="text-base font-semibold">동기화 이력</h2>
        {logsLoading ? (
          <p className="text-sm text-muted-foreground">불러오는 중...</p>
        ) : logs.length === 0 ? (
          <p className="text-sm text-muted-foreground">동기화 이력이 없습니다.</p>
        ) : (
          <div className="rounded-xl border overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  {["상태", "추가", "수정", "삭제", "시각"].map((h) => (
                    <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} className="border-t">
                    <td className="px-4 py-2">
                      {log.status === "success" ? (
                        <span className="flex items-center gap-1 text-green-600">
                          <CheckCircle className="h-3.5 w-3.5" /> 성공
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-destructive">
                          <XCircle className="h-3.5 w-3.5" /> 실패
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-2 tabular-nums">{log.inserted}</td>
                    <td className="px-4 py-2 tabular-nums">{log.updated}</td>
                    <td className="px-4 py-2 tabular-nums">{log.deleted}</td>
                    <td className="px-4 py-2 text-muted-foreground text-xs">
                      {new Date(log.synced_at).toLocaleString("ko-KR")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
