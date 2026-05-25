import type {
  SimulationMeta,
  SimulationRow,
  DerivedRow,
  Scenario,
  ScenarioAPI,
  SimulationDataMultiAPI,
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
    // 사용자 원본 시트의 첫 두 해 변동률(22.35%, 15.25%)
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
  // eop = (bop + flow) * (1 + rate/100) — 시트 공식 동일
  let bop = initialBalance;
  return rows.map((r) => {
    const end = (bop + r.flow) * (1 + r.rate / 100);
    const out: DerivedRow = { ...r, end };
    bop = end;
    return out;
  });
}

export function newScenarioId(): string {
  return `s_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`;
}

export function newScenario(name: string): Scenario {
  return {
    id: newScenarioId(),
    name,
    meta: DEFAULT_META,
    rows: [],
  };
}

// ── API <-> camelCase 변환 ─────────────────────────────────────
export function scenarioToAPI(s: Scenario): ScenarioAPI {
  return {
    id: s.id,
    name: s.name,
    meta: {
      current_age: s.meta.currentAge,
      start_year: s.meta.startYear,
      end_age: s.meta.endAge,
      retire_age: s.meta.retireAge,
      initial_balance_krw: s.meta.initialBalance,
      accum_annual_krw: s.meta.contribution,
      withdrawal_annual_krw: s.meta.withdrawal,
      default_return_rate: s.meta.defaultRate,
    },
    rows: s.rows.map((r) => ({
      age: r.age,
      year: r.year,
      flow_krw: r.flow,
      return_rate: r.rate,
    })),
  };
}

export function scenarioFromAPI(api: ScenarioAPI): Scenario {
  const m = api.meta;
  return {
    id: api.id,
    name: api.name,
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
    rows: api.rows.map((r) => ({
      age: r.age,
      year: r.year,
      flow: r.flow_krw,
      rate: r.return_rate,
    })),
  };
}

export interface ScenarioStore {
  scenarios: Scenario[];
  activeId: string;
}

export function storeToAPI(store: ScenarioStore): SimulationDataMultiAPI {
  return {
    scenarios: store.scenarios.map(scenarioToAPI),
    active_id: store.activeId,
  };
}

export function storeFromAPI(api: SimulationDataMultiAPI): ScenarioStore {
  const scenarios = api.scenarios.map(scenarioFromAPI);
  const activeId =
    api.active_id && scenarios.some((s) => s.id === api.active_id)
      ? api.active_id
      : (scenarios[0]?.id ?? "");
  return { scenarios, activeId };
}
