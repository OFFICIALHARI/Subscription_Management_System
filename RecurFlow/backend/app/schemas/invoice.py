"""Invoice Pydantic v2 schemas aligned with invoices and invoice_lines."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InvoiceLineResponse(BaseModel):
    """Invoice line item representation matching invoice_lines."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    subscription_line_id: int | None = None
    description_snapshot: str
    quantity: int
    unit_price_snapshot: Decimal
    discount_amount: Decimal
    tax_rate_snapshot: Decimal
    line_subtotal: Decimal
    line_tax: Decimal
    line_total: Decimal


class InvoiceResponse(BaseModel):
    """Invoice summary representation matching invoices."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_number: str
    customer_id: int
    subscription_id: int | None = None
    status: str
    currency: str
    subtotal: Decimal
    discount_amount: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    amount_paid: Decimal
    balance_due: Decimal
    billing_period_start: date | None = None
    billing_period_end: date | None = None
    issue_date: date
    due_date: date
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class InvoiceDetailResponse(InvoiceResponse):
    """Invoice detailed representation with line items."""

    lines: list[InvoiceLineResponse] = Field(default_factory=list)
