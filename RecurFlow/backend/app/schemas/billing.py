"""Billing cycle execution and preview Pydantic v2 schemas."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class BillingPreviewItem(BaseModel):
    """A single subscription due for billing."""

    subscription_id: int
    subscription_number: str
    customer_id: int
    customer_name: str
    billing_interval: str
    period_start: date
    period_end: date
    estimated_amount: Decimal
    currency: str


class BillingPreviewResponse(BaseModel):
    """Response containing subscriptions due for recurring billing."""

    run_date: date
    total_due_count: int
    total_estimated_revenue: Decimal
    items: list[BillingPreviewItem] = Field(default_factory=list)


class BillingRunRequest(BaseModel):
    """Payload to trigger a recurring billing execution."""

    run_date: date | None = None  # Defaults to today
    auto_post: bool = True  # Automatically mark invoices as ISSUED


class BillingRunResponse(BaseModel):
    """Summary result of a billing run execution."""

    run_date: date
    invoices_generated: int
    invoices_skipped_idempotent: int
    total_invoiced_amount: Decimal
    generated_invoice_ids: list[int] = Field(default_factory=list)
