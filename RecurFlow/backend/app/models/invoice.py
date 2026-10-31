"""Invoice and invoice line SQLAlchemy ORM models."""

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
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.discount import DiscountApplication
    from app.models.payment import PaymentAllocation
    from app.models.subscription import Subscription, SubscriptionLine


class Invoice(Base):
    """Authoritative commercial billing invoice."""

    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint(
            "subscription_id", "billing_period_start", "billing_period_end",
            name="uq_subscription_billing_period"
        ),
        CheckConstraint(
            "status IN ('DRAFT', 'CONFIRMED', 'PAID', 'PARTIALLY_PAID', 'OVERDUE', 'CANCELLED')",
            name="ck_invoices_status",
        ),
        CheckConstraint("due_date >= issue_date", name="ck_invoices_dates"),
        CheckConstraint(
            "billing_period_start IS NULL OR billing_period_end >= billing_period_start",
            name="ck_invoices_period",
        ),
        CheckConstraint(
            "subtotal >= 0 AND discount_amount >= 0 AND tax_amount >= 0 AND "
            "total_amount >= 0 AND amount_paid >= 0 AND balance_due >= 0 AND "
            "amount_paid <= total_amount AND balance_due = (total_amount - amount_paid)",
            name="ck_invoices_amounts",
        ),
        Index("ix_invoices_status_due_date", "status", "due_date"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customers.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    subscription_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("subscriptions.id", ondelete="RESTRICT"), index=True, nullable=True
    )
    billing_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    issue_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", index=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    balance_due: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    pdf_generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    customer: Mapped["Customer"] = relationship("Customer")
    subscription: Mapped[Optional["Subscription"]] = relationship("Subscription")
    lines: Mapped[list["InvoiceLine"]] = relationship(
        "InvoiceLine", back_populates="invoice", cascade="all, delete-orphan"
    )
    allocations: Mapped[list["PaymentAllocation"]] = relationship(
        "PaymentAllocation", back_populates="invoice"
    )
    discount_applications: Mapped[list["DiscountApplication"]] = relationship(
        "DiscountApplication", back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceLine(Base):
    """Itemized charges on an invoice with historical snapshots."""

    __tablename__ = "invoice_lines"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_invoice_lines_quantity"),
        CheckConstraint("unit_price_snapshot >= 0", name="ck_invoice_lines_price"),
        CheckConstraint("discount_amount >= 0", name="ck_invoice_lines_discount"),
        CheckConstraint("line_subtotal >= 0", name="ck_invoice_lines_subtotal"),
        CheckConstraint("line_tax >= 0", name="ck_invoice_lines_tax"),
        CheckConstraint("line_total >= 0", name="ck_invoice_lines_total"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    invoice_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("invoices.id", ondelete="CASCADE"), index=True, nullable=False
    )
    subscription_line_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("subscription_lines.id", ondelete="SET NULL"), nullable=True
    )
    description_snapshot: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    tax_rate_snapshot: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    line_subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="lines")
    subscription_line: Mapped[Optional["SubscriptionLine"]] = relationship("SubscriptionLine")
