"use client";

interface MonthlyReturn {
  year: number;
  month: number;
  return_rate: number;
}

interface Props {
  data: MonthlyReturn[];
}

const MONTH_LABELS = ["1월", "2월", "3월", "4월", "5월", "6월", "7월", "8월", "9월", "10월", "11월", "12월"];

function cellColor(rate: number): string {
  if (rate > 5) return "bg-[#e31f26] text-white";
  if (rate > 2) return "bg-[#e31f26]/60 text-white";
  if (rate > 0) return "bg-[#e31f26]/25 text-foreground";
  if (rate < -5) return "bg-[#1a56db] text-white";
  if (rate < -2) return "bg-[#1a56db]/60 text-white";
  if (rate < 0) return "bg-[#1a56db]/25 text-foreground";
  return "bg-muted text-muted-foreground";
}

export function MonthlyHeatmap({ data }: Props) {
  if (data.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        스냅샷 데이터가 2개월 이상 쌓이면 표시됩니다.
      </p>
    );
  }

  // Build year → month map
  const byYear: Record<number, Record<number, number>> = {};
  for (const item of data) {
    if (!byYear[item.year]) byYear[item.year] = {};
    byYear[item.year][item.month] = item.return_rate;
  }
  const years = Object.keys(byYear)
    .map(Number)
    .sort((a, b) => b - a); // newest first

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[560px] text-xs border-separate border-spacing-1">
        <thead>
          <tr>
            <th className="w-12 text-left font-medium text-muted-foreground" />
            {MONTH_LABELS.map((m) => (
              <th key={m} className="text-center font-medium text-muted-foreground pb-1">
                {m}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {years.map((year) => (
            <tr key={year}>
              <td className="pr-2 font-medium text-muted-foreground tabular-nums">{year}</td>
              {Array.from({ length: 12 }, (_, i) => i + 1).map((month) => {
                const rate = byYear[year][month];
                return (
                  <td key={month} className="text-center">
                    {rate !== undefined ? (
                      <span
                        className={`inline-block w-full rounded px-0.5 py-1 tabular-nums font-medium ${cellColor(rate)}`}
                        title={`${year}년 ${month}월: ${rate > 0 ? "+" : ""}${rate.toFixed(2)}%`}
                      >
                        {rate > 0 ? "+" : ""}
                        {rate.toFixed(1)}%
                      </span>
                    ) : (
                      <span className="inline-block w-full rounded px-0.5 py-1 bg-muted/30 text-muted-foreground/40">
                        —
                      </span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
