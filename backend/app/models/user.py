from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    kis_app_key_enc: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    kis_app_secret_enc: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    kis_account_no: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    kis_acnt_prdt_cd: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    portfolios: Mapped[List[Portfolio]] = relationship(back_populates="user", cascade="all, delete-orphan")
