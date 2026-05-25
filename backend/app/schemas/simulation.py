from typing import List, Optional

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


class SimulationScenario(BaseModel):
    """단일 시나리오 (시트의 한 탭에 해당)."""

    id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=40)
    meta: SimulationMeta
    rows: List[SimulationRow] = Field(default_factory=list)


class SimulationDataMulti(BaseModel):
    """자산 시뮬레이션 저장 형식 (simulation_params JSONB).

    여러 시나리오(준원/은주/은주퇴직 등)를 보관. `active_id` 는 마지막으로
    열어본 탭. None 이면 첫 번째 시나리오를 기본으로 사용.
    """

    scenarios: List[SimulationScenario] = Field(min_length=1)
    active_id: Optional[str] = None


def normalize_legacy(raw: Optional[dict]) -> Optional[dict]:
    """이전 단일 시나리오 형식 `{meta, rows}` 을 새 다중 형식으로 변환.

    이미 새 형식이면 그대로 반환. 미정/손상 데이터는 None 반환.
    """
    if raw is None:
        return None
    if "scenarios" in raw and isinstance(raw["scenarios"], list):
        return raw
    if "meta" in raw and "rows" in raw:
        return {
            "scenarios": [
                {
                    "id": "default",
                    "name": "기본",
                    "meta": raw["meta"],
                    "rows": raw["rows"],
                }
            ],
            "active_id": "default",
        }
    return None
