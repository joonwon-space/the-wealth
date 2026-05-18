"""backfill kis_accounts.account_type from acnt_prdt_cd and label

Revision ID: o7p8q9r0s1t2
Revises: n6o7p8q9r0s1
Create Date: 2026-05-18 09:30:00.000000

`account_type` 컬럼이 추가되기 전에 등록된 KIS 계좌들은 값이 NULL 로 남아
있어, `kis_order_place._get_domestic_tr_id` 가 항상 기본 일반 매수 TR_ID
(`TTTC0802U`) 로 분기한다. 연금저축(`acnt_prdt_cd='22'`)은 본래
`TTTC0852U` 로 보내야 하므로 기존 데이터를 보정한다.

매핑 규칙(보수적):
  - `acnt_prdt_cd='22'`               → '연금저축'
  - `acnt_prdt_cd='01'` AND label %ISA%  → 'ISA'
  - label %IRP%                         → 'IRP'
  - 그 외 NULL                          → '일반' (기본값)

라벨 매칭은 한글 사용자가 자유 입력하는 값이라 100% 정확하진 않지만,
잘못 매핑되어도 KIS 가 `acnt_prdt_cd` 로 라우팅하므로 거래 자체는 동작.
"""

from typing import Sequence, Union

from alembic import op

revision: str = "o7p8q9r0s1t2"
down_revision: Union[str, None] = "n6o7p8q9r0s1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE kis_accounts
        SET account_type = '연금저축'
        WHERE account_type IS NULL AND acnt_prdt_cd = '22'
        """
    )
    op.execute(
        """
        UPDATE kis_accounts
        SET account_type = 'ISA'
        WHERE account_type IS NULL AND acnt_prdt_cd = '01' AND label LIKE '%ISA%'
        """
    )
    op.execute(
        """
        UPDATE kis_accounts
        SET account_type = 'IRP'
        WHERE account_type IS NULL AND label LIKE '%IRP%'
        """
    )
    op.execute(
        """
        UPDATE kis_accounts
        SET account_type = '일반'
        WHERE account_type IS NULL
        """
    )


def downgrade() -> None:
    # 데이터 backfill 마이그레이션 — 원래 어떤 행이 NULL 이었는지 복원할
    # 방법이 없어 no-op. 필요 시 수동으로 NULL 처리.
    pass
