"""Quotation and QuotationLine Pydantic v2 schemas."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class QuotationLineCreate(BaseModel):
    """Quotation line creation payload."""

    product_id: int
    variant_id: int | None = None
    description: str | None = None
    quantity: int = Field(1, ge=1)
    unit_price: Decimal = Field(..., ge=0)
    tax_rate_id: int | None = None


class QuotationLineResponse(BaseModel):
    """Quotation line representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    quotation_id: int
    product_id: int
    variant_id: int | None = None
    description: str
    quantity: int
    unit_price: Decimal
    discount_amount: Decimal
    subtotal: Decimal
    tax_rate_id: int | None = None
    tax_amount: Decimal
    total_amount: Decimal


class QuotationCreate(BaseModel):
    """Quotation creation payload."""

    customer_id: int
    plan_id: int | None = None
    valid_until: date
    currency: str = "USD"
    discount_code: str | None = None
    tax_rate_id: int | None = None
    terms_conditions: str | None = None
    notes: str | None = None
    lines: list[QuotationLineCreate] = Field(default_factory=list)


class QuotationUpdate(BaseModel):
    """Quotation draft update payload."""

    valid_until: date | None = None
    discount_code: str | None = None
    tax_rate_id: int | None = None
    terms_conditions: str | None = None
    notes: str | None = None
    lines: list[QuotationLineCreate] | None = None


class QuotationResponse(BaseModel):
    """Quotation representation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    quotation_number: str
    customer_id: int
    plan_id: int | None
    status: str
    valid_until: date
    currency: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    terms_conditions: str | None
    notes: str | None
    converted_subscription_id: int | None
    created_at: datetime
    updated_at: datetime


class QuotationDetailResponse(QuotationResponse):
    """Detailed quotation including lines."""

    lines: list[QuotationLineResponse] = Field(default_factory=list)
