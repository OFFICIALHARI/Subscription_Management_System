"""Product catalogue and product variants SQLAlchemy ORM models."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Product(Base):
    """Catalog product offering."""

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("product_type IN ('SERVICE', 'SOFTWARE', 'PHYSICAL')", name="ck_products_type"),
        CheckConstraint("sales_price >= 0", name="ck_products_sales_price"),
        CheckConstraint("cost_price >= 0", name="ck_products_cost_price"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    product_type: Mapped[str] = mapped_column(String(50), default="SERVICE", nullable=False)
    sku: Mapped[str | None] = mapped_column(String(100), unique=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sales_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    cost_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant", back_populates="product", cascade="all, delete-orphan"
    )


class ProductVariant(Base):
    """Specific variant option with configurable price delta (e.g. +560.00)."""

    __tablename__ = "product_variants"
    __table_args__ = (
        UniqueConstraint("product_id", "variant_name", "variant_value", name="uq_product_variant_option"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("products.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    variant_name: Mapped[str] = mapped_column(String(100), nullable=False)
    variant_value: Mapped[str] = mapped_column(String(100), nullable=False)
    sku_suffix: Mapped[str | None] = mapped_column(String(50), nullable=True)
    price_adjustment: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    product: Mapped["Product"] = relationship("Product", back_populates="variants")
