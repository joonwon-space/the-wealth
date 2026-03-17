"use client";

import { useEffect, useState } from "react";
import { Bell, CheckCircle, Eye, Loader2, Moon, Pencil, Plus, Sun, Trash2, Wifi, XCircle } from "lucide-react";
import { useTheme } from "next-themes";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { formatKRW, formatNumber } from "@/lib/format";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

interface BalanceHolding {
  ticker: string;
  name: string;
  quantity: string;
  avg_price: string;
}

interface AccountBalance {
  label: string;
  account_no: string;
  portfolio_id?: number;
  deposit: string;
  total_eval: string;
  stock_eval: string;
  pnl: string;
  synced?: { inserted: number; updated: number; deleted: number };
  holdings: BalanceHolding[];
  error?: string;
}

interface AlertItem {
  id: number;
  ticker: string;
  name: string;
  condition: "above" | "below";
  threshold: number;
  is_active: boolean;
}

export default function SettingsPage() {
  const [balanceLoading, setBalanceLoading] = useState(false);
  const [balanceAccounts, setBalanceAccounts] = useState<AccountBalance[] | null>(null);
  const [balanceError, setBalanceError] = useState<string | null>(null);

  const [kisAccounts, setKisAccounts] = useState<{ id: number; label: string; account_no: string; acnt_prdt_cd: string }[]>([]);
  const [editingAcctId, setEditingAcctId] = useState<number | null>(null);
  const [editLabel, setEditLabel] = useState("");
  const [showAddAccount, setShowAddAccount] = useState(false);
  const [newAcct, setNewAcct] = useState({ label: "", account_no: "", acnt_prdt_cd: "01", app_key: "", app_secret: "" });
  const [addingAcct, setAddingAcct] = useState(false);
  const [testingAcctId, setTestingAcctId] = useState<number | null>(null);
  const [testResults, setTestResults] = useState<Record<number, boolean | null>>({});

  const handleTestAccount = async (id: number) => {
    setTestingAcctId(id);
    setTestResults((prev) => ({ ...prev, [id]: null }));
    try {
      const { data } = await api.post<{ success: boolean; message: string }>(`/users/kis-accounts/${id}/test`);
      setTestResults((prev) => ({ ...prev, [id]: data.success }));
      if (data.success) {
        toast.success(data.message);
      } else {
        toast.error(data.message);
      }
    } catch {
      setTestResults((prev) => ({ ...prev, [id]: false }));
      toast.error("연결 테스트에 실패했습니다");
    } finally {
      setTestingAcctId(null);
    }
  };

  const { theme, setTheme } = useTheme();

  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [newAlert, setNewAlert] = useState({ ticker: "", name: "", condition: "above" as "above" | "below", threshold: "" });
  const [addingAlert, setAddingAlert] = useState(false);

  const fetchKisAccounts = () => {
    api.get<typeof kisAccounts>("/users/kis-accounts").then(({ data }) => setKisAccounts(data));
  };

  const fetchAlerts = () => {
    api.get<AlertItem[]>("/alerts").then(({ data }) => setAlerts(data));
  };

  useEffect(() => {
    fetchKisAccounts();
    fetchAlerts();
  }, []);

  const handleAddAlert = async () => {
    if (!newAlert.ticker || !newAlert.threshold) return;
    setAddingAlert(true);
    try {
      await api.post("/alerts", {
        ticker: newAlert.ticker.toUpperCase(),
        name: newAlert.name,
        condition: newAlert.condition,
        threshold: Number(newAlert.threshold),
      });
      setNewAlert({ ticker: "", name: "", condition: "above", threshold: "" });
      fetchAlerts();
      toast.success("알림이 등록되었습니다");
    } catch {
      toast.error("알림 등록에 실패했습니다");
    } finally {
      setAddingAlert(false);
    }
  };

  const handleDeleteAlert = async (id: number) => {
    try {
      await api.delete(`/alerts/${id}`);
      setAlerts((prev) => prev.filter((a) => a.id !== id));
      toast.success("알림이 삭제되었습니다");
    } catch {
      toast.error("삭제에 실패했습니다");
    }
  };

  const handleAddAccount = async () => {
    if (!newAcct.label || !newAcct.account_no || !newAcct.app_key || !newAcct.app_secret) return;
    setAddingAcct(true);
    try {
      await api.post("/users/kis-accounts", newAcct);
      setNewAcct({ label: "", account_no: "", acnt_prdt_cd: "01", app_key: "", app_secret: "" });
      setShowAddAccount(false);
      fetchKisAccounts();
      toast.success("KIS 계좌가 등록되었습니다");
    } catch {
      toast.error("계좌 등록에 실패했습니다");
    } finally {
      setAddingAcct(false);
    }
  };

  const handleSaveLabel = async (id: number) => {
    if (!editLabel.trim()) return;
    try {
      await api.patch(`/users/kis-accounts/${id}`, { label: editLabel });
      setKisAccounts((prev) => prev.map((a) => a.id === id ? { ...a, label: editLabel } : a));
      setEditingAcctId(null);
      toast.success("계좌 별칭이 변경되었습니다");
    } catch {
      toast.error("별칭 변경에 실패했습니다");
    }
  };

  const handleDeleteAccount = async (id: number) => {
    try {
      await api.delete(`/users/kis-accounts/${id}`);
      setKisAccounts((prev) => prev.filter((a) => a.id !== id));
      toast.success("계좌가 삭제되었습니다");
    } catch {
      toast.error("계좌 삭제에 실패했습니다");
    }
  };

  const handleBalanceInquiry = async () => {
    setBalanceLoading(true);
    setBalanceError(null);
    setBalanceAccounts(null);
    try {
      const { data } = await api.post<{ accounts: AccountBalance[] }>("/sync/balance");
      setBalanceAccounts(data.accounts);
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

      {/* 테마 */}
      <Card>
        <CardContent className="p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold">테마</p>
            <p className="text-xs text-muted-foreground">라이트 / 다크 모드 전환</p>
          </div>
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="flex items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium hover:bg-muted transition-colors"
          >
            {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            {theme === "dark" ? "라이트 모드" : "다크 모드"}
          </button>
        </CardContent>
      </Card>

      {/* KIS 계좌 관리 */}
      <Card>
        <CardContent className="space-y-4 p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold">KIS 계좌 목록</h2>
            <Button size="sm" variant="outline" onClick={() => setShowAddAccount(!showAddAccount)} className="gap-1">
              <Plus className="h-3.5 w-3.5" />
              {showAddAccount ? "취소" : "계좌 추가"}
            </Button>
          </div>

          {showAddAccount && (
            <div className="space-y-2 rounded-lg border p-3">
              <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">별칭</label>
                  <Input value={newAcct.label} onChange={(e) => setNewAcct((f) => ({ ...f, label: e.target.value }))} placeholder="연금저축" className="h-8" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">계좌번호</label>
                  <Input value={newAcct.account_no} onChange={(e) => setNewAcct((f) => ({ ...f, account_no: e.target.value }))} placeholder="63853538" className="h-8 font-mono" />
                </div>
                <div className="space-y-1">
                  <label className="text-xs text-muted-foreground">상품코드</label>
                  <Input value={newAcct.acnt_prdt_cd} onChange={(e) => setNewAcct((f) => ({ ...f, acnt_prdt_cd: e.target.value }))} placeholder="01" className="h-8 font-mono w-16" />
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">App Key</label>
                <Input value={newAcct.app_key} onChange={(e) => setNewAcct((f) => ({ ...f, app_key: e.target.value }))} placeholder="PS7yzJ..." className="h-8 font-mono" />
              </div>
              <div className="space-y-1">
                <label className="text-xs text-muted-foreground">App Secret</label>
                <Input type="password" value={newAcct.app_secret} onChange={(e) => setNewAcct((f) => ({ ...f, app_secret: e.target.value }))} placeholder="••••••••" className="h-8" />
              </div>
              <Button size="sm" onClick={handleAddAccount} disabled={addingAcct}>
                {addingAcct ? "등록 중..." : "등록"}
              </Button>
            </div>
          )}

          {kisAccounts.length === 0 ? (
            <p className="text-sm text-muted-foreground">등록된 KIS 계좌가 없습니다.</p>
          ) : (
            <div className="space-y-2">
              {kisAccounts.map((a) => (
                <div key={a.id} className="flex items-center justify-between rounded-lg border px-3 py-2 text-sm">
                  {editingAcctId === a.id ? (
                    <div className="flex items-center gap-2">
                      <Input value={editLabel} onChange={(e) => setEditLabel(e.target.value)} className="h-7 w-32" autoFocus />
                      <Button size="sm" onClick={() => handleSaveLabel(a.id)} className="h-7 px-2 text-xs">저장</Button>
                      <Button size="sm" variant="outline" onClick={() => setEditingAcctId(null)} className="h-7 px-2 text-xs">취소</Button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1">
                      <span className="font-medium">{a.label}</span>
                      <button onClick={() => { setEditingAcctId(a.id); setEditLabel(a.label); }} className="text-muted-foreground/50 hover:text-muted-foreground">
                        <Pencil className="h-3 w-3" />
                      </button>
                      <span className="ml-1 font-mono text-muted-foreground">{a.account_no}-{a.acnt_prdt_cd}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-1.5">
                    <button
                      onClick={() => handleTestAccount(a.id)}
                      disabled={testingAcctId === a.id}
                      className="rounded border px-2 py-0.5 text-xs text-muted-foreground hover:bg-muted disabled:opacity-50 flex items-center gap-1"
                      title="연결 테스트"
                    >
                      {testingAcctId === a.id ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : testResults[a.id] === true ? (
                        <CheckCircle className="h-3 w-3 text-green-600" />
                      ) : testResults[a.id] === false ? (
                        <XCircle className="h-3 w-3 text-destructive" />
                      ) : (
                        <Wifi className="h-3 w-3" />
                      )}
                      테스트
                    </button>
                    <button onClick={() => handleDeleteAccount(a.id)} className="text-muted-foreground hover:text-destructive">
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 실계좌 조회 + 동기화 */}
      <Card>
        <CardContent className="space-y-4 p-6">
          <h2 className="text-base font-semibold">실계좌 조회 & 동기화</h2>
          <p className="text-sm text-muted-foreground">
            등록된 KIS 계좌의 보유 종목을 조회하고 포트폴리오에 자동 동기화합니다.
          </p>
          <Button onClick={handleBalanceInquiry} disabled={balanceLoading} className="gap-2">
            <Eye className="h-4 w-4" />
            {balanceLoading ? "조회 중..." : "실계좌 조회 & 동기화"}
          </Button>
          {balanceError && (
            <p className="text-sm text-destructive">{balanceError}</p>
          )}
          {balanceAccounts !== null && balanceAccounts.map((acct) => (
            <div key={acct.account_no} className="space-y-3">
              <h3 className="text-sm font-semibold">
                {acct.label} <span className="font-normal text-muted-foreground">({acct.account_no})</span>
              </h3>
              {acct.error ? (
                <p className="text-sm text-destructive">{acct.error}</p>
              ) : (
                <>
                  {acct.synced && (acct.synced.inserted > 0 || acct.synced.updated > 0 || acct.synced.deleted > 0) && (
                    <p className="text-xs text-green-600">
                      동기화: +{acct.synced.inserted} ~{acct.synced.updated} -{acct.synced.deleted}
                    </p>
                  )}
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    <div className="rounded-lg border p-3">
                      <p className="text-xs text-muted-foreground">예수금</p>
                      <p className="font-semibold tabular-nums">{formatKRW(acct.deposit)}</p>
                    </div>
                    <div className="rounded-lg border p-3">
                      <p className="text-xs text-muted-foreground">총 평가</p>
                      <p className="font-semibold tabular-nums">{formatKRW(acct.total_eval)}</p>
                    </div>
                    <div className="rounded-lg border p-3">
                      <p className="text-xs text-muted-foreground">주식 평가</p>
                      <p className="font-semibold tabular-nums">{formatKRW(acct.stock_eval)}</p>
                    </div>
                    <div className="rounded-lg border p-3">
                      <p className="text-xs text-muted-foreground">평가 손익</p>
                      <p className="font-semibold tabular-nums">{formatKRW(acct.pnl)}</p>
                    </div>
                  </div>
                  {acct.holdings.length === 0 ? (
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
                          {acct.holdings.map((h) => (
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
            </div>
          ))}
        </CardContent>
      </Card>

      {/* 목표가 알림 */}
      <Card>
        <CardContent className="p-4 space-y-4">
          <div className="flex items-center gap-2">
            <Bell className="h-4 w-4" />
            <h2 className="text-base font-semibold">목표가 알림</h2>
          </div>

          {/* 등록 폼 */}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
            <Input
              placeholder="티커 (예: 005930)"
              value={newAlert.ticker}
              onChange={(e) => setNewAlert((p) => ({ ...p, ticker: e.target.value }))}
              className="uppercase"
            />
            <Input
              placeholder="종목명 (선택)"
              value={newAlert.name}
              onChange={(e) => setNewAlert((p) => ({ ...p, name: e.target.value }))}
            />
            <select
              value={newAlert.condition}
              onChange={(e) => setNewAlert((p) => ({ ...p, condition: e.target.value as "above" | "below" }))}
              className="rounded-md border bg-background px-3 py-2 text-sm"
            >
              <option value="above">이상 (≥)</option>
              <option value="below">이하 (≤)</option>
            </select>
            <Input
              type="number"
              placeholder="목표가"
              value={newAlert.threshold}
              onChange={(e) => setNewAlert((p) => ({ ...p, threshold: e.target.value }))}
            />
            <Button onClick={handleAddAlert} disabled={addingAlert || !newAlert.ticker || !newAlert.threshold} size="sm">
              {addingAlert ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
              추가
            </Button>
          </div>

          {/* 알림 목록 */}
          {alerts.length === 0 ? (
            <p className="text-sm text-muted-foreground py-2">등록된 알림이 없습니다.</p>
          ) : (
            <div className="divide-y rounded-lg border">
              {alerts.map((a) => (
                <div key={a.id} className="flex items-center justify-between px-4 py-2.5">
                  <div className="text-sm">
                    <span className="font-medium">{a.name || a.ticker}</span>
                    {a.name && <span className="ml-1 text-xs text-muted-foreground">({a.ticker})</span>}
                    <span className="ml-2 text-muted-foreground">
                      {a.condition === "above" ? "≥" : "≤"} {formatKRW(a.threshold)}
                    </span>
                  </div>
                  <button
                    onClick={() => handleDeleteAlert(a.id)}
                    className="rounded p-1 text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

    </div>
  );
}
