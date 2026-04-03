"use client";

import { useEffect, useState } from "react";
import { Bell, Loader2, Moon, Plus, Sun, Trash2 } from "lucide-react";
import { useTheme } from "next-themes";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { formatKRW } from "@/lib/format";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { AccountSection } from "./AccountSection";
import { KisCredentialsSection } from "./KisCredentialsSection";
import { SecurityLogsSection } from "./SecurityLogsSection";
import { ActiveSessionsSection } from "./ActiveSessionsSection";

interface AlertItem {
  id: number;
  ticker: string;
  name: string;
  condition: "above" | "below";
  threshold: number;
  is_active: boolean;
}

type SettingsTab = "account" | "kis" | "alerts" | "security";

const TABS: { id: SettingsTab; label: string }[] = [
  { id: "account", label: "계정" },
  { id: "kis", label: "KIS 계좌" },
  { id: "alerts", label: "알림" },
  { id: "security", label: "보안" },
];

export default function SettingsPage(): React.ReactElement {
  const [activeTab, setActiveTab] = useState<SettingsTab>("account");
  const { theme, setTheme } = useTheme();

  // Alerts state
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [newAlert, setNewAlert] = useState({
    ticker: "",
    name: "",
    condition: "above" as "above" | "below",
    threshold: "",
  });
  const [addingAlert, setAddingAlert] = useState(false);

  const fetchAlerts = () => {
    api.get<AlertItem[]>("/alerts").then(({ data }) => setAlerts(data));
  };

  useEffect(() => {
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

  return (
    <div className="space-y-6 max-w-xl">
      <h1 className="text-2xl font-bold">설정</h1>

      {/* 테마 토글 (항상 상단에 표시) */}
      <Card>
        <CardContent className="p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-semibold">테마</p>
            <p className="text-xs text-muted-foreground">
              라이트 / 다크 모드 전환
            </p>
          </div>
          <button
            onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
            className="flex min-h-[44px] items-center gap-2 rounded-lg border px-3 py-2 text-sm font-medium hover:bg-muted transition-colors"
          >
            {theme === "dark" ? (
              <Sun className="h-4 w-4" aria-hidden="true" />
            ) : (
              <Moon className="h-4 w-4" aria-hidden="true" />
            )}
            {theme === "dark" ? "라이트 모드" : "다크 모드"}
          </button>
        </CardContent>
      </Card>

      {/* 탭 네비게이션 */}
      <div className="flex gap-1 border-b">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
              activeTab === tab.id
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 탭 콘텐츠 */}
      <div className="space-y-6">
        {activeTab === "account" && <AccountSection />}

        {activeTab === "kis" && <KisCredentialsSection />}

        {activeTab === "alerts" && (
          <Card>
            <CardContent className="p-4 space-y-4">
              <div className="flex items-center gap-2">
                <Bell className="h-4 w-4" aria-hidden="true" />
                <h2 className="text-base font-semibold">목표가 알림</h2>
              </div>

              <div className="flex flex-col gap-2 sm:grid sm:grid-cols-5">
                <Input
                  aria-label="티커"
                  placeholder="티커 (예: 005930)"
                  value={newAlert.ticker}
                  onChange={(e) =>
                    setNewAlert((p) => ({ ...p, ticker: e.target.value }))
                  }
                  className="uppercase h-11 sm:h-9"
                />
                <Input
                  aria-label="종목명"
                  placeholder="종목명 (선택)"
                  value={newAlert.name}
                  onChange={(e) =>
                    setNewAlert((p) => ({ ...p, name: e.target.value }))
                  }
                  className="h-11 sm:h-9"
                />
                <select
                  aria-label="조건"
                  value={newAlert.condition}
                  onChange={(e) =>
                    setNewAlert((p) => ({
                      ...p,
                      condition: e.target.value as "above" | "below",
                    }))
                  }
                  className="h-11 sm:h-9 rounded-md border bg-background px-3 py-2 text-sm"
                >
                  <option value="above">이상 (≥)</option>
                  <option value="below">이하 (≤)</option>
                </select>
                <Input
                  aria-label="목표가"
                  type="number"
                  placeholder="목표가"
                  value={newAlert.threshold}
                  onChange={(e) =>
                    setNewAlert((p) => ({ ...p, threshold: e.target.value }))
                  }
                  className="h-11 sm:h-9"
                />
                <Button
                  onClick={handleAddAlert}
                  disabled={
                    addingAlert || !newAlert.ticker || !newAlert.threshold
                  }
                  className="h-11 sm:h-9 gap-1"
                >
                  {addingAlert ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Plus className="h-3.5 w-3.5" aria-hidden="true" />
                  )}
                  추가
                </Button>
              </div>

              {alerts.length === 0 ? (
                <p className="text-sm text-muted-foreground py-2">
                  등록된 알림이 없습니다.
                </p>
              ) : (
                <div className="divide-y rounded-lg border">
                  {alerts.map((a) => (
                    <div
                      key={a.id}
                      className="flex items-center justify-between px-4 py-2.5"
                    >
                      <div className="text-sm">
                        <span className="font-medium">{a.name || a.ticker}</span>
                        {a.name && (
                          <span className="ml-1 text-xs text-muted-foreground">
                            ({a.ticker})
                          </span>
                        )}
                        <span className="ml-2 text-muted-foreground">
                          {a.condition === "above" ? "≥" : "≤"}{" "}
                          {formatKRW(a.threshold)}
                        </span>
                      </div>
                      <button
                        onClick={() => handleDeleteAlert(a.id)}
                        aria-label={`${a.name || a.ticker} 알림 삭제`}
                        className="min-h-[44px] min-w-[44px] flex items-center justify-center rounded text-muted-foreground hover:text-destructive"
                      >
                        <Trash2 className="h-4 w-4" aria-hidden="true" />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {activeTab === "security" && (
          <>
            <SecurityLogsSection />
            <ActiveSessionsSection />
          </>
        )}
      </div>
    </div>
  );
}
