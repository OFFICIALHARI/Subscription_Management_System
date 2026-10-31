"""Tax rules SQLAlchemy ORM model."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TaxRate(Base):
    """Tax statutory rules and percentage rates."""

    __tablename__ = "tax_rates"
    __table_args__ = (
        CheckConstraint("rate_percentage >= 0 AND rate_percentage <= 100", name="ck_tax_rates_rate"),
        CheckConstraint("tax_type IN ('EXCLUSIVE', 'INCLUSIVE')", name="ck_tax_rates_type"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    rate_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    tax_type: Mapped[str] = mapped_column(String(50), default="EXCLUSIVE", nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
