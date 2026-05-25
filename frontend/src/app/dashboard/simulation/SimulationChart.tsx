"use client";

import { useLayoutEffect, useRef, useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import type { DerivedRow } from "./types";
import { krw, shortKrw } from "./formatters";

interface HoverState {
  age: number;
  end: number;
  x: number;
  y: number;
}

interface Props {
  data: DerivedRow[];
  retireAge: number;
  height?: number;
}

export function SimulationChart({ data, retireAge, height = 280 }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(800);
  const [hover, setHover] = useState<HoverState | null>(null);

  useLayoutEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => {
      if (e) setWidth(Math.max(280, Math.floor(e.contentRect.width)));
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  if (!data.length) return null;

  const padL = 12;
  const padR = 12;
  const padT = 16;
  const padB = 28;
  const W = width;
  const H = height;

  const ages = data.map((r) => r.age);
  const minAge = Math.min(...ages);
  const maxAge = Math.max(...ages);
  const vals = data.map((r) => r.end);
  const maxV = Math.max(...vals) * 1.05;

  const xPos = (age: number) =>
    padL + ((age - minAge) / (maxAge - minAge)) * (W - padL - padR);
  const yPos = (v: number) =>
    padT + (1 - v / maxV) * (H - padT - padB);

  const linePath = data
    .map(
      (r, i) =>
        `${i === 0 ? "M" : "L"}${xPos(r.age).toFixed(1)},${yPos(r.end).toFixed(1)}`,
    )
    .join(" ");
  const areaPath = `${linePath} L${xPos(maxAge).toFixed(1)},${yPos(0).toFixed(1)} L${xPos(minAge).toFixed(1)},${yPos(0).toFixed(1)} Z`;

  const niceMax = Math.ceil(maxV / 5e8) * 5e8 || maxV;
  const yTicks = [0, niceMax * 0.25, niceMax * 0.5, niceMax * 0.75, niceMax].filter(
    (t) => t <= maxV * 1.1,
  );
  const xTicks = ages.filter(
    (a) => a % 10 === 0 || a === minAge || a === maxAge,
  );

  const onMouseMove = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = e.clientX - rect.left;
    const t = (px - padL) / (W - padL - padR);
    const age = Math.round(minAge + t * (maxAge - minAge));
    const r = data.find((d) => d.age === age);
    if (r) setHover({ age, end: r.end, x: xPos(age), y: yPos(r.end) });
  };

  return (
    <Card className="shadow-none">
      <CardHeader className="pb-2 pt-4 px-4">
        <div className="flex items-baseline justify-between">
          <div>
            <p className="text-sm font-semibold">연말 잔고 추이</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {minAge}세 → {maxAge}세 · 은퇴 {retireAge}세
            </p>
          </div>
        </div>
      </CardHeader>
      <CardContent className="px-3 pb-3">
        <div
          ref={wrapRef}
          className="relative w-full"
          style={{ height: H }}
          onMouseLeave={() => setHover(null)}
        >
          <svg
            width={W}
            height={H}
            onMouseMove={onMouseMove}
            style={{ display: "block", cursor: "crosshair" }}
          >
            <defs>
              <linearGradient id="simAreaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor="var(--rise)"
                  stopOpacity="0.22"
                />
                <stop
                  offset="100%"
                  stopColor="var(--rise)"
                  stopOpacity="0"
                />
              </linearGradient>
            </defs>
            {yTicks.map((t, i) => (
              <g key={i}>
                <line
                  x1={padL}
                  x2={W - padR}
                  y1={yPos(t)}
                  y2={yPos(t)}
                  stroke="var(--border)"
                  strokeDasharray={i === 0 ? "0" : "2 3"}
                  strokeWidth="1"
                />
                <text
                  x={padL}
                  y={yPos(t) - 4}
                  fontSize={10}
                  fill="var(--muted-foreground)"
                  style={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {shortKrw(t)}
                </text>
              </g>
            ))}
            {xTicks.map((a) => (
              <text
                key={a}
                x={xPos(a)}
                y={H - 6}
                textAnchor="middle"
                fontSize={10}
                fill="var(--muted-foreground)"
                style={{ fontVariantNumeric: "tabular-nums" }}
              >
                {a}
              </text>
            ))}
            <path d={areaPath} fill="url(#simAreaGrad)" />
            <path
              d={linePath}
              fill="none"
              stroke="var(--rise)"
              strokeWidth="1.75"
              strokeLinejoin="round"
              strokeLinecap="round"
            />
            {retireAge >= minAge && retireAge <= maxAge && (
              <g>
                <line
                  x1={xPos(retireAge)}
                  x2={xPos(retireAge)}
                  y1={padT}
                  y2={H - padB}
                  stroke="var(--muted-foreground)"
                  strokeDasharray="3 3"
                  strokeWidth="1"
                />
                <text
                  x={xPos(retireAge) + 4}
                  y={padT + 10}
                  fontSize={10}
                  fill="var(--muted-foreground)"
                  fontWeight="500"
                >
                  은퇴 {retireAge}
                </text>
              </g>
            )}
            {hover && (
              <g>
                <line
                  x1={hover.x}
                  x2={hover.x}
                  y1={padT}
                  y2={H - padB}
                  stroke="currentColor"
                  strokeOpacity="0.2"
                  strokeWidth="1"
                />
                <circle
                  cx={hover.x}
                  cy={hover.y}
                  r={4}
                  fill="white"
                  stroke="var(--rise)"
                  strokeWidth="2"
                />
              </g>
            )}
          </svg>
          {hover && (
            <div
              className="pointer-events-none absolute rounded-md border bg-popover px-2.5 py-1.5 text-xs shadow-md"
              style={{
                left: Math.min(W - 130, Math.max(0, hover.x + 10)),
                top: Math.max(0, hover.y - 48),
              }}
            >
              <p className="text-muted-foreground">{hover.age}세</p>
              <p className="font-semibold tabular-nums">{krw(hover.end)}</p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
