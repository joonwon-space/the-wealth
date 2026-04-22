"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft,
  ArrowRight,
  BookOpen,
  CheckCircle2,
  KeyRound,
  Star,
  Target,
  Zap,
} from "lucide-react";
import { toast } from "sonner";
import { api } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { ModeToggle, type InvestMode } from "@/components/mode-toggle";
import { StockSearchDialog } from "@/components/StockSearchDialog";
import { cn } from "@/lib/utils";

type Step = 1 | 2 | 3 | 4 | 5;

interface Stocklet {
  ticker: string;
  name: string;
  market: string;
}

const STEP_LABELS: Record<Step, string> = {
  1: "KIS 연동",
  2: "투자 전략",
  3: "목표 설정",
  4: "관심 종목",
  5: "완료",
};

export default function OnboardingPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [step, setStep] = useState<Step>(1);

  // Step 2
  const [strategy, setStrategy] = useState<InvestMode | "mixed">("mixed");
  const [longRatio, setLongRatio] = useState(70);

  // Step 3
  const [goalAmount, setGoalAmount] = useState<string>("");
  const [goalMonths, setGoalMonths] = useState<string>("24");
  const [portfolioName, setPortfolioName] = useState("");

  // Step 4
  const [watchlist, setWatchlist] = useState<Stocklet[]>([]);
  const [searchOpen, setSearchOpen] = useState(false);

  const saveStrategy = useMutation({
    mutationFn: async () => {
      await api.patch("/users/me", {
        strategy_tag: strategy,
        long_short_ratio: strategy === "mixed" ? longRatio : strategy === "long" ? 100 : 0,
      });
    },
  });

  const createPortfolio = useMutation({
    mutationFn: async () => {
      const name = portfolioName.trim() || "기본 포트폴리오";
      const amountRaw = goalAmount.replace(/[^0-9]/g, "");
      const amount = amountRaw ? Number(amountRaw) : null;
      const { data } = await api.post<{ id: number }>("/portfolios", {
        name,
        currency: "KRW",
      });
      if (amount && amount > 0) {
        await api.patch(`/portfolios/${data.id}`, { target_value: amount });
      }
      return data.id;
    },
  });

  const addWatchItem = useMutation({
    mutationFn: async (item: Stocklet) => {
      await api.post("/watchlist", {
        ticker: item.ticker,
        name: item.name,
        market: item.market,
      });
    },
  });

  async function finish() {
    try {
      await saveStrategy.mutateAsync();
      await createPortfolio.mutateAsync();
      for (const w of watchlist) {
        try {
          await addWatchItem.mutateAsync(w);
        } catch {
          // ignore duplicates / individual failures
        }
      }
      await queryClient.invalidateQueries();
      toast.success("온보딩이 완료되었습니다!");
      router.push("/dashboard");
    } catch (err) {
      const message = err instanceof Error ? err.message : "오류가 발생했습니다.";
      toast.error(`완료에 실패했습니다: ${message}`);
    }
  }

  return (
    <div className="mx-auto flex min-h-svh max-w-lg flex-col gap-6 p-6">
      <header className="space-y-1">
        <p className="text-xs font-semibold uppercase tracking-widest text-muted-foreground">
          {step} / 5 · {STEP_LABELS[step]}
        </p>
        <h1 className="text-2xl font-bold tracking-tight">
          The Wealth 시작하기
        </h1>
      </header>

      <div className="flex gap-1.5" role="progressbar" aria-valuenow={step} aria-valuemin={1} aria-valuemax={5}>
        {[1, 2, 3, 4, 5].map((s) => (
          <div
            key={s}
            className={cn(
              "h-1.5 flex-1 rounded-full transition-colors",
              s <= step ? "bg-primary" : "bg-muted",
            )}
          />
        ))}
      </div>

      <div className="flex-1">
        {step === 1 && <StepKis onNext={() => setStep(2)} onSkip={() => setStep(2)} />}
        {step === 2 && (
          <StepStrategy
            strategy={strategy}
            onStrategy={setStrategy}
            longRatio={longRatio}
            onLongRatio={setLongRatio}
            onNext={() => setStep(3)}
          />
        )}
        {step === 3 && (
          <StepGoal
            goalAmount={goalAmount}
            onGoalAmount={setGoalAmount}
            goalMonths={goalMonths}
            onGoalMonths={setGoalMonths}
            portfolioName={portfolioName}
            onPortfolioName={setPortfolioName}
            onNext={() => setStep(4)}
          />
        )}
        {step === 4 && (
          <StepWatchlist
            items={watchlist}
            onChange={setWatchlist}
            onOpenSearch={() => setSearchOpen(true)}
            onNext={() => setStep(5)}
          />
        )}
        {step === 5 && <StepDone onGo={finish} saving={saveStrategy.isPending || createPortfolio.isPending} />}
      </div>

      {step > 1 && step < 5 && (
        <button
          type="button"
          onClick={() => setStep((prev) => (Math.max(1, prev - 1) as Step))}
          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3" /> 뒤로
        </button>
      )}

      <StockSearchDialog
        open={searchOpen}
        onClose={() => setSearchOpen(false)}
        onSelect={(ticker, name) => {
          setSearchOpen(false);
          setWatchlist((prev) => {
            if (prev.some((w) => w.ticker === ticker)) return prev;
            const market = /^[A-Z]+$/.test(ticker) ? "NYSE" : "KRX";
            return [...prev, { ticker, name, market }];
          });
        }}
      />
    </div>
  );
}

// ----- Step 1: KIS -----
function StepKis({ onNext, onSkip }: { onNext: () => void; onSkip: () => void }) {
  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-3 p-6 text-center">
          <KeyRound className="mx-auto size-8 text-primary" />
          <p className="text-base font-semibold">한국투자증권 API 연결</p>
          <p className="text-sm text-muted-foreground">
            보유 종목·잔고·주문을 실시간으로 가져오려면 KIS OpenAPI 키가 필요합니다.
            나중에 설정 → KIS 계좌에서도 연결할 수 있습니다.
          </p>
        </CardContent>
      </Card>
      <div className="flex gap-2">
        <button
          type="button"
          onClick={onSkip}
          className="flex-1 rounded-md border border-border bg-card px-4 py-2.5 text-sm font-semibold text-muted-foreground hover:bg-muted"
        >
          나중에 연결
        </button>
        <button
          type="button"
          onClick={onNext}
          className="flex-1 rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90"
        >
          다음
          <ArrowRight className="inline ml-1 size-3" />
        </button>
      </div>
    </div>
  );
}

// ----- Step 2: Strategy -----
function StepStrategy({
  strategy,
  onStrategy,
  longRatio,
  onLongRatio,
  onNext,
}: {
  strategy: "long" | "short" | "mixed";
  onStrategy: (s: "long" | "short" | "mixed") => void;
  longRatio: number;
  onLongRatio: (v: number) => void;
  onNext: () => void;
}) {
  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-4 p-6">
          <p className="text-sm text-muted-foreground">
            투자 스타일을 알려주시면 홈 화면이 맞춰 바뀝니다.
          </p>
          <div className="grid grid-cols-3 gap-2">
            <StrategyCard
              icon={<BookOpen className="size-4" />}
              label="장기"
              desc="적립·장기 가치"
              active={strategy === "long"}
              onClick={() => onStrategy("long")}
            />
            <StrategyCard
              icon={<Zap className="size-4" />}
              label="단타"
              desc="실시간 단타"
              active={strategy === "short"}
              onClick={() => onStrategy("short")}
            />
            <StrategyCard
              icon={<Star className="size-4" />}
              label="혼합"
              desc="장기+단타"
              active={strategy === "mixed"}
              onClick={() => onStrategy("mixed")}
            />
          </div>

          {strategy === "mixed" && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">장기 비중</span>
                <span className="font-bold tabular-nums">{longRatio}%</span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={longRatio}
                onChange={(e) => onLongRatio(Number(e.target.value))}
                className="w-full accent-[color:var(--primary)]"
                aria-label="장기 비중 슬라이더"
              />
              <div className="flex justify-between text-[11px] text-muted-foreground">
                <span>단타 {100 - longRatio}%</span>
                <span>장기 {longRatio}%</span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
      <NextButton onClick={onNext} />
    </div>
  );
}

function StrategyCard({
  icon,
  label,
  desc,
  active,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  desc: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-lg border px-3 py-3 text-left transition-colors",
        active
          ? "border-primary bg-primary/10 text-foreground"
          : "border-border bg-card hover:bg-muted/40",
      )}
    >
      <div className="flex items-center gap-1.5 text-sm font-bold">
        {icon}
        {label}
      </div>
      <p className="mt-1 text-[11px] text-muted-foreground">{desc}</p>
    </button>
  );
}

// ----- Step 3: Goal -----
function StepGoal({
  goalAmount,
  onGoalAmount,
  goalMonths,
  onGoalMonths,
  portfolioName,
  onPortfolioName,
  onNext,
}: {
  goalAmount: string;
  onGoalAmount: (v: string) => void;
  goalMonths: string;
  onGoalMonths: (v: string) => void;
  portfolioName: string;
  onPortfolioName: (v: string) => void;
  onNext: () => void;
}) {
  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-4 p-6">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Target className="size-4" /> 첫 포트폴리오 + 목표를 함께 설정합니다.
          </div>
          <label className="flex flex-col gap-1 text-sm">
            포트폴리오 이름
            <Input
              value={portfolioName}
              onChange={(e) => onPortfolioName(e.target.value)}
              placeholder="예: 적립식, 연금저축"
              maxLength={100}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            목표 금액 (원)
            <Input
              inputMode="numeric"
              value={goalAmount}
              onChange={(e) => onGoalAmount(e.target.value.replace(/[^0-9,]/g, ""))}
              placeholder="예: 200000000 (2억)"
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            목표 기간 (개월)
            <Input
              inputMode="numeric"
              value={goalMonths}
              onChange={(e) => onGoalMonths(e.target.value.replace(/[^0-9]/g, ""))}
              placeholder="예: 24"
            />
          </label>
        </CardContent>
      </Card>
      <NextButton onClick={onNext} />
    </div>
  );
}

// ----- Step 4: Watchlist -----
function StepWatchlist({
  items,
  onChange,
  onOpenSearch,
  onNext,
}: {
  items: Stocklet[];
  onChange: (list: Stocklet[]) => void;
  onOpenSearch: () => void;
  onNext: () => void;
}) {
  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-3 p-6">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Star className="size-4" /> 자주 보는 종목 3개 이상 추천합니다.
          </div>
          {items.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">
              아직 없음 — 아래 버튼으로 추가하세요.
            </p>
          ) : (
            <div className="space-y-1.5">
              {items.map((w) => (
                <div
                  key={w.ticker}
                  className="flex items-center justify-between rounded-md border border-border bg-card px-3 py-2 text-sm"
                >
                  <span className="font-semibold">{w.name}</span>
                  <div className="flex items-center gap-2">
                    <Badge tone="neutral">{w.market}</Badge>
                    <button
                      type="button"
                      onClick={() =>
                        onChange(items.filter((x) => x.ticker !== w.ticker))
                      }
                      className="text-xs text-muted-foreground hover:text-destructive"
                    >
                      제거
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
          <button
            type="button"
            onClick={onOpenSearch}
            className="w-full rounded-md border border-dashed border-border px-4 py-2.5 text-sm font-semibold text-muted-foreground hover:bg-muted/40"
          >
            + 관심종목 추가
          </button>
        </CardContent>
      </Card>
      <NextButton onClick={onNext} label={items.length === 0 ? "건너뛰기" : "다음"} />
    </div>
  );
}

// ----- Step 5: Done -----
function StepDone({ onGo, saving }: { onGo: () => void; saving: boolean }) {
  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="space-y-3 p-8 text-center">
          <CheckCircle2 className="mx-auto size-10 text-primary" />
          <p className="text-lg font-bold">준비 완료!</p>
          <p className="text-sm text-muted-foreground">
            홈 화면에서 오늘의 변동·목표 진척도·섹터 배분·배당 일정을 한 번에 확인하세요.
          </p>
          <div className="flex justify-center">
            <ModeToggle mode="long" onChange={() => {}} position="header" />
          </div>
        </CardContent>
      </Card>
      <button
        type="button"
        onClick={onGo}
        disabled={saving}
        className="w-full rounded-md bg-primary px-4 py-3 text-sm font-bold text-primary-foreground hover:opacity-90 disabled:opacity-50"
      >
        {saving ? (
          <Skeleton className="mx-auto h-4 w-20" />
        ) : (
          "홈으로 이동"
        )}
      </button>
    </div>
  );
}

function NextButton({ onClick, label = "다음" }: { onClick: () => void; label?: string }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full rounded-md bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:opacity-90"
    >
      {label}
      <ArrowRight className="inline ml-1 size-3" />
    </button>
  );
}
