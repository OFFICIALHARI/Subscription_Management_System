"""Quotation Pydantic v2 schemas aligned with quotations and quotation_lines."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class QuotationLineCreate(BaseModel):
    """Quotation line creation payload."""

    product_id: int
    product_variant_id: int | None = None
    plan_id: int | None = None
    description: str | None = None
    quantity: int = Field(1, ge=1)
    unit_price: Decimal = Field(..., ge=0)
    discount_rate: Decimal = Field(default=Decimal("0.00"), ge=0, le=100)
    tax_rate_id: int | None = None


class QuotationLineResponse(BaseModel):
    """Quotation line representation matching quotation_lines."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    quotation_id: int
    product_id: int
    product_variant_id: int | None = None
    plan_id: int | None = None
    description_snapshot: str
    quantity: int
    unit_price_snapshot: Decimal
    discount_rate: Decimal
    tax_rate_id: int | None = None
    tax_rate_snapshot: Decimal
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal


class QuotationCreate(BaseModel):
    """Quotation creation payload.

    plan_id is accepted as a convenience to pre-fill lines from plan items.
    It is stored on generated quotation lines, not on the quotation header
    (the quotations table has no plan_id column).
    """

    customer_id: int
    plan_id: int | None = None
    issue_date: date | None = None
    expiration_date: date
    currency: str = "USD"
    discount_code: str | None = None
    tax_rate_id: int | None = None
    notes: str | None = None
    template_id: int | None = None
    lines: list[QuotationLineCreate] = Field(default_factory=list)


class QuotationResponse(BaseModel):
    """Quotation representation matching quotations."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    quotation_number: str
    customer_id: int
    template_id: int | None
    status: str
    issue_date: date
    expiration_date: date
    currency: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    is_converted: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime


class QuotationDetailResponse(QuotationResponse):
    """Detailed quotation including lines."""

    lines: list[QuotationLineResponse] = Field(default_factory=list)
