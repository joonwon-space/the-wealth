from typing import List

from pydantic import BaseModel, Field


class SimulationMeta(BaseModel):
    current_age: int = Field(ge=1, le=120)
    start_year: int = Field(ge=2000, le=2200)
    end_age: int = Field(ge=1, le=120)
    retire_age: int = Field(ge=1, le=120)
    initial_balance_krw: int = Field(ge=0)
    accum_annual_krw: int = Field(ge=0)
    withdrawal_annual_krw: int = Field(ge=0)
    default_return_rate: float = Field(ge=-100.0, le=1000.0)


class SimulationRow(BaseModel):
    age: int = Field(ge=1, le=120)
    year: int = Field(ge=2000, le=2200)
    flow_krw: int
    return_rate: float = Field(ge=-100.0, le=1000.0)


class SimulationData(BaseModel):
    """자산 시뮬레이션 저장 형식 (simulation_params JSONB)."""

    meta: SimulationMeta
    rows: List[SimulationRow] = Field(default_factory=list)
