"""Product, Variant, Plan, and PlanItem Pydantic v2 schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


# --- Product Variants ---
class ProductVariantBase(BaseModel):
    """Base product variant fields."""

    sku: str
    name: str
    attribute_values: dict[str, str] = Field(default_factory=dict)
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


# --- Products ---
class ProductBase(BaseModel):
    """Base product fields."""

    name: str
    code: str
    description: str | None = None
    base_price: Decimal = Field(..., ge=0)
    tax_rate_id: int | None = None
    is_active: bool = True


class ProductCreate(ProductBase):
    """Product creation payload."""

    variants: list[ProductVariantCreate] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    """Product update payload."""

    name: str | None = None
    code: str | None = None
    description: str | None = None
    base_price: Decimal | None = None
    tax_rate_id: int | None = None
    is_active: bool | None = None


class ProductResponse(ProductBase):
    """Product representation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    variants: list[ProductVariantResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# --- Plan Items ---
class PlanItemBase(BaseModel):
    """Base plan item fields."""

    product_id: int
    variant_id: int | None = None
    quantity: int = Field(1, ge=1)
    unit_price: Decimal = Field(..., ge=0)
    sort_order: int = 0


class PlanItemCreate(PlanItemBase):
    """Plan item creation payload."""

    pass


class PlanItemResponse(PlanItemBase):
    """Plan item representation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    created_at: datetime


# --- Plans ---
class PlanBase(BaseModel):
    """Base plan fields."""

    code: str
    name: str
    description: str | None = None
    billing_interval: str  # DAILY, WEEKLY, MONTHLY, YEARLY
    interval_count: int = 1
    trial_period_days: int = 0
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
    is_active: bool | None = None


class PlanResponse(PlanBase):
    """Plan representation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    items: list[PlanItemResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
