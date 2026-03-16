import { BarChart3 } from "lucide-react";

export default function AnalyticsPage() {
  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold">분석</h1>
      <div className="flex flex-col items-center justify-center rounded-xl border border-dashed py-20 text-center">
        <BarChart3 className="mb-3 h-12 w-12 text-muted-foreground/40" />
        <p className="text-lg font-semibold">준비 중입니다</p>
        <p className="mt-1 text-sm text-muted-foreground">
          포트폴리오 성과 분석, 섹터별 배분, 벤치마크 비교 기능이 곧 추가됩니다.
        </p>
      </div>
    </div>
  );
}
