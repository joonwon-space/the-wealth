"use client";

import { useState } from "react";
import {
  BookOpen,
  Coins,
  Scale,
  Target,
  TrendingUp,
  Wallet,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Donut } from "@/components/charts/donut";
import { HeatCell } from "@/components/charts/heat-cell";
import { ProgressRing } from "@/components/charts/progress-ring";
import { HeroValue } from "@/components/hero-value";
import { ModeToggle, type InvestMode } from "@/components/mode-toggle";
import { RangeIndicator } from "@/components/range-indicator";
import { SectorBar } from "@/components/sector-bar";
import { StreamCard } from "@/components/stream/stream-card";
import { TaskCard } from "@/components/task-card";

const sectors = [
  { sector: "IT", pct: 0.45, target: 0.3, color: "var(--chart-1)" },
  { sector: "소재", pct: 0.2, target: 0.2, color: "var(--chart-3)" },
  { sector: "금융", pct: 0.15, target: 0.2, color: "var(--chart-5)" },
  { sector: "헬스케어", pct: 0.2, target: 0.3, color: "var(--chart-6)" },
];

const heatmap = [2.3, -1.4, 4.8, 0.8, -2.2, 1.1];

export default function DesignPreviewPage() {
  const [mode, setMode] = useState<InvestMode>("long");

  return (
    <div className="mx-auto max-w-[960px] space-y-8 p-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-bold tracking-tight">Design Preview · Step 1 컴포넌트</h1>
        <p className="text-sm text-muted-foreground">
          redesign-spec.md §10 단계 1의 신규 shadcn 컴포넌트 10종 시각 확인용 라우트.
        </p>
      </header>

      <Section title="HeroValue">
        <HeroValue
          label="총 평가금액 · KRW"
          value="₩42,180,500"
          change="+₩1,204,000"
          changePct={1.84}
          footnote="USD/KRW 1,380"
          trailing={<ProgressRing pct={0.42} size={72} thickness={7} />}
        />
      </Section>

      <Section title="ModeToggle (inline / header)">
        <div className="space-y-3">
          <ModeToggle mode={mode} onChange={setMode} ratio={{ long: 70, short: 30 }} />
          <ModeToggle mode={mode} onChange={setMode} position="header" />
        </div>
      </Section>

      <Section title="Badge tones">
        <div className="flex flex-wrap gap-2">
          <Badge tone="neutral">보합</Badge>
          <Badge tone="rise">+1.84%</Badge>
          <Badge tone="fall">-2.10%</Badge>
          <Badge tone="warn">리밸런싱</Badge>
          <Badge tone="ok">체결 완료</Badge>
          <Badge tone="primary">KIS</Badge>
          <Badge tone="rise" solid>
            알림
          </Badge>
          <Badge tone="primary" solid>
            Solid
          </Badge>
        </div>
      </Section>

      <Section title="ProgressRing + Donut + HeatCell">
        <div className="flex flex-wrap items-center gap-6">
          <ProgressRing pct={0.42} size={96} thickness={10} label="42%" />
          <Donut
            size={112}
            thickness={14}
            segments={sectors.map((s) => ({
              pct: s.pct,
              color: s.color,
              label: s.sector,
            }))}
            center={
              <div>
                <div className="text-[10px] uppercase tracking-wide text-muted-foreground">섹터</div>
                <div className="text-sm font-bold">{sectors.length}</div>
              </div>
            }
          />
          <div className="grid grid-cols-6 gap-1.5">
            {heatmap.map((v, i) => (
              <HeatCell key={i} pct={v} />
            ))}
          </div>
        </div>
      </Section>

      <Section title="SectorBar">
        <div className="space-y-3 rounded-lg border border-border bg-card p-4">
          {sectors.map((s) => (
            <SectorBar key={s.sector} {...s} />
          ))}
        </div>
      </Section>

      <Section title="RangeIndicator (52주)">
        <div className="rounded-lg border border-border bg-card p-4">
          <RangeIndicator low={58200} high={92400} current={71200} />
        </div>
      </Section>

      <Section title="TaskCard">
        <div className="space-y-2">
          <TaskCard
            icon={<Scale />}
            title="IT 섹터 비중 조정"
            sub="현재 45% · 목표 30%"
            accent="var(--accent-amber)"
          />
          <TaskCard
            icon={<Target />}
            title="목표까지 70,550k 남음"
            sub="예상 14개월"
            accent="var(--primary)"
          />
          <TaskCard
            icon={<Wallet />}
            title="예수금 1,200,000 대기 중"
            sub="사용 가능"
            accent="var(--chart-6)"
          />
        </div>
      </Section>

      <Section title="StreamCard (5종)">
        <div className="space-y-2">
          <StreamCard
            kind="alert"
            title="NVIDIA — $145 돌파"
            sub="목표 $140 이상 · 현재 $145.22 (+3.42%)"
            ts="14:32 · 방금"
          >
            <div className="flex gap-2">
              <Button size="sm" variant="outline">
                종목 보기
              </Button>
              <Button size="sm" className="bg-rise text-white hover:bg-rise/90">
                매도 주문
              </Button>
            </div>
          </StreamCard>
          <StreamCard
            kind="rebalance"
            title="IT 섹터 45% · 목표 30% 초과"
            sub="15%p 차이 · 삼성전자 일부 정리 권장"
            ts="09:00 · 5시간 전"
          />
          <StreamCard
            kind="fill"
            title="삼성전자 매수 · 10주 @ 72,400"
            sub="주문번호 #A1203"
            ts="09:12 · 오늘"
          />
          <StreamCard
            kind="dividend"
            title="삼성전자 분기배당"
            sub="배당락 4/28 · 지급 5/15 · +430"
            ts="4/28 예정"
          />
          <StreamCard
            kind="routine"
            title="월간 리밸런싱 체크"
            sub="매월 1일 진행"
            ts="4/30"
          >
            <div className="flex gap-2">
              <Button size="sm" variant="outline">
                <BookOpen className="mr-1" /> 시작
              </Button>
            </div>
          </StreamCard>
        </div>
      </Section>

      <Section title="Stream 아이콘 팔레트 테스트">
        <div className="flex flex-wrap gap-2 text-muted-foreground">
          <TrendingUp className="size-5" />
          <Coins className="size-5" />
          <Target className="size-5" />
        </div>
      </Section>
    </div>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="space-y-3">
      <h2 className="text-section-header">{title}</h2>
      {children}
    </section>
  );
}
