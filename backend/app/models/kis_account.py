from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class KisAccount(Base):
    __tablename__ = "kis_accounts"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "account_no", "acnt_prdt_cd", name="uq_kis_account_per_user"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    label: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # e.g. "연금저축", "ISA"
    account_no: Mapped[str] = mapped_column(String(20), nullable=False)
    acnt_prdt_cd: Mapped[str] = mapped_column(String(5), nullable=False, default="01")
    app_key_enc: Mapped[str] = mapped_column(String(512), nullable=False)
    app_secret_enc: Mapped[str] = mapped_column(String(512), nullable=False)
    is_paper_trading: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    account_type: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, default=None
    )  # 일반, ISA, 연금저축, IRP, 해외주식
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
