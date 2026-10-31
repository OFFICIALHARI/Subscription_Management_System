"""Discounts and discount redemption tracking SQLAlchemy ORM models."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.invoice import Invoice


class Discount(Base):
    """Discount campaign rules, limits, and promo codes."""

    __tablename__ = "discounts"
    __table_args__ = (
        CheckConstraint("discount_type IN ('PERCENTAGE', 'FIXED_AMOUNT')", name="ck_discounts_type"),
        CheckConstraint(
            "(discount_type = 'PERCENTAGE' AND discount_value > 0 AND discount_value <= 100) OR "
            "(discount_type = 'FIXED_AMOUNT' AND discount_value > 0)",
            name="ck_discounts_value",
        ),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_discounts_dates"),
        CheckConstraint("min_order_amount >= 0", name="ck_discounts_min_order"),
        CheckConstraint("uses_count >= 0", name="ck_discounts_uses_count"),
        CheckConstraint("max_uses_per_customer >= 1", name="ck_discounts_max_per_customer"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    discount_type: Mapped[str] = mapped_column(String(20), nullable=False)
    discount_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    min_order_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    max_uses_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    uses_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_uses_per_customer: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DiscountApplication(Base):
    """Transactional record of discount redeemed against an invoice."""

    __tablename__ = "discount_applications"
    __table_args__ = (
        CheckConstraint("applied_amount > 0", name="ck_discount_apps_amount"),
        Index("ix_discount_apps_customer", "discount_id", "customer_id"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    discount_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("discounts.id", ondelete="RESTRICT"), nullable=False
    )
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False
    )
    invoice_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False
    )
    applied_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    discount: Mapped["Discount"] = relationship("Discount")
    customer: Mapped["Customer"] = relationship("Customer")
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="discount_applications")
