"""Quotation and quotation template SQLAlchemy ORM models."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.plan import Plan
    from app.models.product import Product, ProductVariant
    from app.models.tax import TaxRate


class QuotationTemplate(Base):
    """Reusable quote template blueprints."""

    __tablename__ = "quotation_templates"
    __table_args__ = (
        CheckConstraint("default_validity_days >= 1", name="ck_quotation_templates_validity"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    default_validity_days: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Quotation(Base):
    """Commercial proposals issued to customers."""

    __tablename__ = "quotations"
    __table_args__ = (
        CheckConstraint(
            "status IN ('DRAFT', 'SENT', 'CONFIRMED', 'CANCELLED', 'EXPIRED')",
            name="ck_quotations_status",
        ),
        CheckConstraint("expiration_date >= issue_date", name="ck_quotations_dates"),
        CheckConstraint("subtotal >= 0", name="ck_quotations_subtotal"),
        CheckConstraint("discount_amount >= 0", name="ck_quotations_discount"),
        CheckConstraint("tax_amount >= 0", name="ck_quotations_tax"),
        CheckConstraint("total_amount >= 0", name="ck_quotations_total"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    quotation_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    customer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("customers.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    template_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("quotation_templates.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", index=True, nullable=False)
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiration_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    is_converted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    customer: Mapped["Customer"] = relationship("Customer")
    template: Mapped[Optional["QuotationTemplate"]] = relationship("QuotationTemplate")
    lines: Mapped[list["QuotationLine"]] = relationship(
        "QuotationLine", back_populates="quotation", cascade="all, delete-orphan"
    )


class QuotationLine(Base):
    """Itemized quotation line with frozen snapshots."""

    __tablename__ = "quotation_lines"
    __table_args__ = (
        CheckConstraint("quantity >= 1", name="ck_quotation_lines_quantity"),
        CheckConstraint("unit_price_snapshot >= 0", name="ck_quotation_lines_price"),
        CheckConstraint("discount_rate >= 0 AND discount_rate <= 100", name="ck_quotation_lines_discount_rate"),
        CheckConstraint("line_subtotal >= 0", name="ck_quotation_lines_subtotal"),
        CheckConstraint("line_tax >= 0", name="ck_quotation_lines_tax"),
        CheckConstraint("line_total >= 0", name="ck_quotation_lines_total"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    quotation_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("quotations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="RESTRICT"), nullable=False
    )
    product_variant_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("product_variants.id", ondelete="RESTRICT"), nullable=True
    )
    plan_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("plans.id", ondelete="RESTRICT"), nullable=True
    )
    description_snapshot: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price_snapshot: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    tax_rate_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("tax_rates.id", ondelete="SET NULL"), nullable=True
    )
    tax_rate_snapshot: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("0.00"), nullable=False)
    line_subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    quotation: Mapped["Quotation"] = relationship("Quotation", back_populates="lines")
    product: Mapped["Product"] = relationship("Product")
    variant: Mapped[Optional["ProductVariant"]] = relationship("ProductVariant")
    plan: Mapped[Optional["Plan"]] = relationship("Plan")
    tax_rate: Mapped[Optional["TaxRate"]] = relationship("TaxRate")
