"""Subscription lifecycle, lines, and event timeline SQLAlchemy ORM models."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
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
    from app.models.plan import Plan
    from app.models.product import Product, ProductVariant
    from app.models.quotation import Quotation, QuotationLine
    from app.models.tax import TaxRate
    from app.models.user import User


class Subscription(Base):
    """Active contractual recurring commitment."""

    __tablename__ = "subscriptions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'QUOTATION', 'CONFIRMED', 'ACTIVE', 'PAUSED', 'CLOSED')",
            name="ck_subscriptions_status",
        ),
        CheckConstraint("billing_anchor_day BETWEEN 1 AND 31", name="ck_subscriptions_anchor"),
        CheckConstraint("end_date IS NULL OR end_date >= start_date", name="ck_subscriptions_dates"),
        CheckConstraint("recurring_amount >= 0", name="ck_subscriptions_recurring"),
        CheckConstraint("payment_terms_days >= 0", name="ck_subscriptions_payment_terms"),
        Index("ix_subscriptions_status_billing_date", "status", "next_billing_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    subscription_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customers.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    plan_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("plans.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    originating_quotation_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("quotations.id", ondelete="SET NULL"), index=True, nullable=True
    )
    renewed_from_subscription_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("subscriptions.id", ondelete="SET NULL"), index=True, nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", index=True, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_anchor_day: Mapped[int] = mapped_column(Integer, nullable=False)
    next_billing_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    payment_terms_days: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    recurring_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    auto_close_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    customer: Mapped["Customer"] = relationship("Customer")
    plan: Mapped["Plan"] = relationship("Plan")
    originating_quotation: Mapped[Optional["Quotation"]] = relationship("Quotation")
    renewed_from: Mapped[Optional["Subscription"]] = relationship(
        "Subscription", remote_side=[id], foreign_keys=[renewed_from_subscription_id]
    )
    lines: Mapped[list["SubscriptionLine"]] = relationship(
        "SubscriptionLine", back_populates="subscription", cascade="all, delete-orphan"
    )
    events: Mapped[list["SubscriptionEvent"]] = relationship(
        "SubscriptionEvent", back_populates="subscription", cascade="all, delete-orphan"
    )


class SubscriptionLine(Base):
    """Recurring product items attached to the subscription."""

    __tablename__ = "subscription_lines"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_sub_lines_quantity"),
        CheckConstraint("unit_price_snapshot >= 0", name="ck_sub_lines_price"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    product_variant_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=True
    )
    quotation_line_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("quotation_lines.id", ondelete="SET NULL"), index=True, nullable=True
    )
    description_snapshot: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_rate_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tax_rates.id", ondelete="SET NULL"), nullable=True
    )
    tax_rate_snapshot: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="lines")
    product: Mapped["Product"] = relationship("Product")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")
    quotation_line: Mapped[Optional["QuotationLine"]] = relationship("QuotationLine")
    tax_rate: Mapped[Optional["TaxRate"]] = relationship("TaxRate")


class SubscriptionEvent(Base):
    """Audit timeline of state changes for subscriptions."""

    __tablename__ = "subscription_events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    actor_user_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    from_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    to_status: Mapped[str] = mapped_column(String(20), nullable=False)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    subscription: Mapped["Subscription"] = relationship("Subscription", back_populates="events")
    actor: Mapped[Optional["User"]] = relationship("User")
