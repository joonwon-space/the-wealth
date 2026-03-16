"use client";

import { useEffect, useState } from "react";
import { Eye, RefreshCw, CheckCircle, XCircle } from "lucide-react";
import { api } from "@/lib/api";
import { formatKRW, formatNumber } from "@/lib/format";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

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

interface BalanceHolding {
  ticker: string;
  name: string;
  quantity: string;
  avg_price: string;
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

  const [balanceLoading, setBalanceLoading] = useState(false);
  const [balanceData, setBalanceData] = useState<{
    deposit: string;
    total_eval: string;
    stock_eval: string;
    pnl: string;
    holdings: BalanceHolding[];
  } | null>(null);
  const [balanceError, setBalanceError] = useState<string | null>(null);

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
        `/sync/${selectedPortfolio}`
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

  const handleBalanceInquiry = async () => {
    setBalanceLoading(true);
    setBalanceError(null);
    setBalanceData(null);
    try {
      const { data } = await api.get<{
        account_no: string;
        deposit: string;
        total_eval: string;
        stock_eval: string;
        pnl: string;
        holdings: BalanceHolding[];
      }>("/sync/balance");
      setBalanceData(data);
    } catch (err: unknown) {
      const msg = err && typeof err === "object" && "response" in err
        ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
        : null;
      setBalanceError(msg ?? "조회에 실패했습니다");
    } finally {
      setBalanceLoading(false);
    }
  };

  return (
    <div className="space-y-8 max-w-xl">
      <h1 className="text-2xl font-bold">설정</h1>

      {/* KIS 자격증명 */}
      <Card>
        <CardContent className="space-y-4 p-6">
          <h2 className="text-base font-semibold">KIS OpenAPI 자격증명</h2>
          <p className="text-sm text-muted-foreground">
            한국투자증권 OpenAPI 앱키와 시크릿을 입력하세요. AES-256으로 암호화하여 저장됩니다.
          </p>
          <form onSubmit={handleCredSave} className="space-y-3">
            <div className="space-y-1">
              <label className="text-sm font-medium">앱키 (App Key)</label>
              <Input
                type="text"
                value={appKey}
                onChange={(e) => setAppKey(e.target.value)}
                placeholder="PS7yzJ..."
                className="font-mono"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">앱시크릿 (App Secret)</label>
              <Input
                type="password"
                value={appSecret}
                onChange={(e) => setAppSecret(e.target.value)}
                placeholder="••••••••"
              />
            </div>
            <div className="space-y-1">
              <label className="text-sm font-medium">계좌번호 (선택)</label>
              <Input
                type="text"
                value={accountNo}
                onChange={(e) => setAccountNo(e.target.value)}
                placeholder="63853538"
                className="font-mono"
              />
            </div>
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={credSaving || !appKey || !appSecret}>
                {credSaving ? "저장 중..." : "저장"}
              </Button>
              {credSuccess && (
                <span className="flex items-center gap-1 text-sm text-green-600">
                  <CheckCircle className="h-4 w-4" /> 저장되었습니다
                </span>
              )}
            </div>
          </form>
        </CardContent>
      </Card>

      {/* 계좌 동기화 */}
      <Card>
        <CardContent className="space-y-4 p-6">
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
            <Button onClick={handleSync} disabled={syncing || !selectedPortfolio} className="gap-2">
              <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
              {syncing ? "동기화 중..." : "지금 동기화"}
            </Button>
          </div>
          {syncResult && (
            <p className={`text-sm ${syncResult.startsWith("오류") ? "text-destructive" : "text-green-600"}`}>
              {syncResult}
            </p>
          )}
        </CardContent>
      </Card>

      {/* 실계좌 조회 */}
      <Card>
        <CardContent className="space-y-4 p-6">
          <h2 className="text-base font-semibold">실계좌 보유 종목 조회</h2>
          <p className="text-sm text-muted-foreground">
            KIS 실계좌의 현재 보유 종목을 조회합니다 (동기화 없이 조회만).
          </p>
          <Button onClick={handleBalanceInquiry} disabled={balanceLoading} className="gap-2">
            <Eye className="h-4 w-4" />
            {balanceLoading ? "조회 중..." : "실계좌 조회"}
          </Button>
          {balanceError && (
            <p className="text-sm text-destructive">{balanceError}</p>
          )}
          {balanceData !== null && (
            <>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">예수금</p>
                  <p className="font-semibold tabular-nums">{formatKRW(balanceData.deposit)}</p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">총 평가</p>
                  <p className="font-semibold tabular-nums">{formatKRW(balanceData.total_eval)}</p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">주식 평가</p>
                  <p className="font-semibold tabular-nums">{formatKRW(balanceData.stock_eval)}</p>
                </div>
                <div className="rounded-lg border p-3">
                  <p className="text-xs text-muted-foreground">평가 손익</p>
                  <p className="font-semibold tabular-nums">{formatKRW(balanceData.pnl)}</p>
                </div>
              </div>
              {balanceData.holdings.length === 0 ? (
                <p className="text-sm text-muted-foreground">보유 종목이 없습니다.</p>
              ) : (
                <div className="rounded-lg border overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-muted/50">
                      <tr>
                        {["종목", "수량", "평균단가"].map((h) => (
                          <th key={h} className="px-4 py-2 text-left font-medium text-muted-foreground">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {balanceData.holdings.map((h) => (
                        <tr key={h.ticker} className="border-t">
                          <td className="px-4 py-2">
                            <div className="font-medium">{h.name}</div>
                            <div className="text-xs text-muted-foreground">{h.ticker}</div>
                          </td>
                          <td className="px-4 py-2 tabular-nums">{formatNumber(h.quantity)}</td>
                          <td className="px-4 py-2 tabular-nums">{formatKRW(h.avg_price)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>

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
