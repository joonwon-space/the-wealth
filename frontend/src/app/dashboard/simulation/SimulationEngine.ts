import type {
  SimulationMeta,
  SimulationRow,
  DerivedRow,
  SimulationSummaryData,
  SimulationDataAPI,
} from "./types";

export const DEFAULT_META: SimulationMeta = {
  currentAge: 32,
  startYear: 2024,
  endAge: 100,
  retireAge: 55,
  initialBalance: 0,
  contribution: 4_800_000,
  withdrawal: 15_000_000,
  defaultRate: 7.0,
};

export function buildRows(meta: SimulationMeta): SimulationRow[] {
  const rows: SimulationRow[] = [];
  for (let age = meta.currentAge; age <= meta.endAge; age++) {
    const year = meta.startYear + (age - meta.currentAge);
    const isAccum = age < meta.retireAge;
    let rate = meta.defaultRate;
    // First two years get sample variance to match the user's original spreadsheet
    if (age === meta.currentAge) rate = 22.35;
    else if (age === meta.currentAge + 1) rate = 15.25;
    const flow = isAccum
      ? age === meta.currentAge
        ? Math.round(meta.contribution * 0.825)
        : meta.contribution
      : -meta.withdrawal;
    rows.push({ age, year, flow, rate });
  }
  return rows;
}

export function computeDerived(
  rows: SimulationRow[],
  initialBalance: number,
): DerivedRow[] {
  let start = initialBalance;
  let cumContrib = 0;
  let cumGain = 0;
  return rows.map((r) => {
    const end = (start + r.flow) * (1 + r.rate / 100);
    const gain = end - (start + r.flow);
    cumContrib += Math.max(0, r.flow);
    cumGain += gain;
    const out: DerivedRow = { ...r, start, end, cumContrib, cumGain };
    start = end;
    return out;
  });
}

export function summarize(
  derived: DerivedRow[],
  retireAge: number,
): SimulationSummaryData | null {
  if (!derived.length) return null;
  const last = derived[derived.length - 1]!;
  const lastAccum =
    [...derived].reverse().find((r) => r.age < retireAge) ?? derived[0]!;
  const totalContrib = derived.reduce((s, r) => s + Math.max(0, r.flow), 0);
  const totalWithdraw = derived.reduce((s, r) => s + Math.max(0, -r.flow), 0);
  return {
    endBalance: last.end,
    lastAccumBalance: lastAccum.end,
    totalContrib,
    totalWithdraw,
    totalGain: last.cumGain,
    avgRate: derived.reduce((s, r) => s + r.rate, 0) / derived.length,
  };
}

export function metaToAPI(
  meta: SimulationMeta,
  rows: SimulationRow[],
): SimulationDataAPI {
  return {
    meta: {
      current_age: meta.currentAge,
      start_year: meta.startYear,
      end_age: meta.endAge,
      retire_age: meta.retireAge,
      initial_balance_krw: meta.initialBalance,
      accum_annual_krw: meta.contribution,
      withdrawal_annual_krw: meta.withdrawal,
      default_return_rate: meta.defaultRate,
    },
    rows: rows.map((r) => ({
      age: r.age,
      year: r.year,
      flow_krw: r.flow,
      return_rate: r.rate,
    })),
  };
}

export function metaFromAPI(data: SimulationDataAPI): {
  meta: SimulationMeta;
  rows: SimulationRow[];
} {
  const m = data.meta;
  return {
    meta: {
      currentAge: m.current_age,
      startYear: m.start_year,
      endAge: m.end_age,
      retireAge: m.retire_age,
      initialBalance: m.initial_balance_krw,
      contribution: m.accum_annual_krw,
      withdrawal: m.withdrawal_annual_krw,
      defaultRate: m.default_return_rate,
    },
    rows: data.rows.map((r) => ({
      age: r.age,
      year: r.year,
      flow: r.flow_krw,
      rate: r.return_rate,
    })),
  };
}
