"""Product, Variant, Plan, and PlanItem Pydantic v2 schemas aligned with ORM models."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductVariantBase(BaseModel):
    """Base product variant fields matching product_variants."""

    variant_name: str = Field(..., min_length=1, max_length=100)
    variant_value: str = Field(..., min_length=1, max_length=100)
    sku_suffix: str | None = None
    price_adjustment: Decimal = Decimal("0.00")
    is_active: bool = True


class ProductVariantCreate(ProductVariantBase):
    """Variant creation payload."""

    pass


class ProductVariantResponse(ProductVariantBase):
    """Variant representation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    created_at: datetime
    updated_at: datetime


class ProductBase(BaseModel):
    """Base product fields matching products."""

    name: str = Field(..., min_length=1, max_length=255)
    product_type: str = Field(default="SERVICE", pattern="^(SERVICE|SOFTWARE|PHYSICAL)$")
    sku: str | None = None
    description: str | None = None
    sales_price: Decimal = Field(..., ge=0)
    cost_price: Decimal = Field(default=Decimal("0.00"), ge=0)
    is_active: bool = True


class ProductCreate(ProductBase):
    """Product creation payload."""

    variants: list[ProductVariantCreate] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    """Product update payload."""

    name: str | None = None
    product_type: str | None = None
    sku: str | None = None
    description: str | None = None
    sales_price: Decimal | None = None
    cost_price: Decimal | None = None
    is_active: bool | None = None


class ProductResponse(ProductBase):
    """Product representation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    variants: list[ProductVariantResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PlanItemBase(BaseModel):
    """Base plan item fields matching plan_items."""

    product_id: int
    product_variant_id: int | None = None
    quantity: int = Field(1, ge=1)
    unit_price: Decimal = Field(..., ge=0)


class PlanItemCreate(PlanItemBase):
    """Plan item creation payload."""

    pass


class PlanItemResponse(PlanItemBase):
    """Plan item representation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    created_at: datetime


class PlanBase(BaseModel):
    """Base plan fields matching plans."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = None
    billing_interval: str = Field(..., pattern="^(DAILY|WEEKLY|MONTHLY|YEARLY|daily|weekly|monthly|yearly)$")
    interval_count: int = Field(1, ge=1)
    trial_period_days: int = Field(0, ge=0)
    minimum_quantity: int = Field(1, ge=1)
    is_active: bool = True


class PlanCreate(PlanBase):
    """Plan creation payload."""

    items: list[PlanItemCreate] = Field(default_factory=list)


class PlanUpdate(BaseModel):
    """Plan update payload."""

    name: str | None = None
    description: str | None = None
    billing_interval: str | None = None
    interval_count: int | None = None
    trial_period_days: int | None = None
    minimum_quantity: int | None = None
    is_active: bool | None = None


class PlanResponse(PlanBase):
    """Plan representation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    items: list[PlanItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
