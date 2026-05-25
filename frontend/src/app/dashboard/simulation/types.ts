export interface SimulationMeta {
  currentAge: number;
  startYear: number;
  endAge: number;
  retireAge: number;
  initialBalance: number;
  contribution: number;
  withdrawal: number;
  defaultRate: number;
}

export interface SimulationRow {
  age: number;
  year: number;
  flow: number;
  rate: number;
}

export interface DerivedRow extends SimulationRow {
  end: number;
}

export interface SimulationDataAPI {
  meta: {
    current_age: number;
    start_year: number;
    end_age: number;
    retire_age: number;
    initial_balance_krw: number;
    accum_annual_krw: number;
    withdrawal_annual_krw: number;
    default_return_rate: number;
  };
  rows: Array<{
    age: number;
    year: number;
    flow_krw: number;
    return_rate: number;
  }>;
}
