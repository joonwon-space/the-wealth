// 백엔드 schemas.analytics 와 1:1 매칭. 응답을 그대로 사용.

export interface AnnualReturnRow {
  year: number;
  age: number | null;
  bop_value_krw: number;
  contributions_krw: number;
  dividends_krw: number;
  eop_value_krw: number;
  pnl_amount_krw: number;
  irr_year: number | null;
  irr_cumulative: number | null;
}

export interface SimulationInput {
  current_value_krw: number;
  current_age: number;
  retirement_age: number;
  end_age: number;
  annual_contribution_krw: number;
  annual_withdrawal_krw: number;
  expected_return_rate: number;
}

export interface SimulationPoint {
  age: number;
  year: number;
  flow_krw: number;
  return_amount_krw: number;
  eop_value_krw: number;
}
