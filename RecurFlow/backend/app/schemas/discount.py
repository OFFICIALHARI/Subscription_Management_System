"""Discount Pydantic v2 schemas aligned with the discounts ORM model."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DiscountBase(BaseModel):
    """Base discount fields matching discounts."""

    code: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=255)
    discount_type: str = Field(..., pattern="^(PERCENTAGE|FIXED_AMOUNT|percentage|fixed_amount)$")
    discount_value: Decimal = Field(..., gt=0)
    min_order_amount: Decimal = Decimal("0.00")
    max_uses_total: int | None = None
    max_uses_per_customer: int = Field(1, ge=1)
    start_date: date | None = None
    end_date: date | None = None
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
    max_uses_per_customer: int | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None


class DiscountResponse(DiscountBase):
    """Discount representation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    uses_count: int
    created_at: datetime
    updated_at: datetime


class DiscountValidationRequest(BaseModel):
    """Payload to validate a discount coupon against an order amount."""

    code: str
    order_amount: Decimal


class DiscountValidationResponse(BaseModel):
    """Result of discount coupon validation."""

    valid: bool
    message: str
    discount_type: str | None = None
    discount_value: Decimal | None = None
    calculated_discount_amount: Decimal = Decimal("0.00")
