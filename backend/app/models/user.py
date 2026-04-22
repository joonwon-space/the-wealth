from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import DateTime, Enum, SmallInteger, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.portfolio import Portfolio


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    # Dual-brain 투자 성향. 'long'(장기) / 'short'(단타) / 'mixed'(혼합)
    strategy_tag: Mapped[str] = mapped_column(
        Enum("long", "short", "mixed", name="strategy_tag"),
        nullable=False,
        server_default="mixed",
    )
    # 혼합 전략에서 장기 비중(%) — 0..100. 단타 비중은 100 - long_short_ratio.
    long_short_ratio: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, server_default="70"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    portfolios: Mapped[List["Portfolio"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
