"""Discount and Promotion Pydantic v2 schemas."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DiscountBase(BaseModel):
    """Base discount fields."""

    code: str
    name: str
    discount_type: str  # PERCENTAGE, FIXED_AMOUNT
    discount_value: Decimal = Field(..., gt=0)
    currency: str = "USD"
    min_order_amount: Decimal = Decimal("0.00")
    max_uses_total: int | None = None
    starts_at: date | None = None
    ends_at: date | None = None
    is_active: bool = True


class DiscountCreate(DiscountBase):
    """Discount creation payload."""

    pass


class DiscountUpdate(BaseModel):
    """Discount update payload."""

    name: str | None = None
    discount_value: Decimal | None = None
    min_order_amount: Decimal | None = None
    max_uses_total: int | None = None
    starts_at: date | None = None
    ends_at: date | None = None
    is_active: bool | None = None


class DiscountResponse(DiscountBase):
    """Discount representation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    uses_count: int
    created_at: datetime
    updated_at: datetime


class DiscountValidationRequest(BaseModel):
    """Payload to validate discount coupon code against order amount."""

    code: str
    order_amount: Decimal


class DiscountValidationResponse(BaseModel):
    """Result of discount coupon validation."""

    valid: bool
    message: str
    discount_type: str | None = None
    discount_value: Decimal | None = None
    calculated_discount_amount: Decimal = Decimal("0.00")
