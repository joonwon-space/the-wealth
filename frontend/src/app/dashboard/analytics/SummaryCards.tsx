"use client";

import { Card, CardContent } from "@/components/ui/card";
import { formatKRW } from "@/lib/format";
import { PnLBadge } from "@/components/PnLBadge";

interface SummaryCardsProps {
  totalAsset: number;
  totalInvested: number;
  totalPnlAmount: number;
  totalPnlRate: number;
}

export function SummaryCards({
  totalAsset,
  totalInvested,
  totalPnlAmount,
  totalPnlRate,
}: SummaryCardsProps) {
  return (
    <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
      <Card>
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">총 자산</p>
          <p className="mt-1 text-lg font-bold tabular-nums">{formatKRW(totalAsset)}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">투자 원금</p>
          <p className="mt-1 text-lg font-bold tabular-nums">{formatKRW(totalInvested)}</p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">총 손익</p>
          <p className="mt-1 text-lg font-bold">
            <PnLBadge value={totalPnlAmount} />
          </p>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground">수익률</p>
          <p className="mt-1 text-lg font-bold">
            <PnLBadge value={totalPnlRate} suffix="%" />
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
