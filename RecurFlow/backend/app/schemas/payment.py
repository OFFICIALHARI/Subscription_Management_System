"""Payment and PaymentAllocation Pydantic v2 schemas."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PaymentAllocationCreate(BaseModel):
    """Payload to allocate an existing payment to an invoice."""

    invoice_id: int
    amount: Decimal = Field(..., gt=0)


class PaymentAllocationResponse(BaseModel):
    """Payment allocation record representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_id: int
    invoice_id: int
    allocated_amount: Decimal
    allocation_date: datetime
    reversed_at: datetime | None


class PaymentBase(BaseModel):
    """Base payment fields."""

    customer_id: int
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    payment_method: str = "MANUAL"
    payment_date: date | None = None
    notes: str | None = None


class PaymentCreate(PaymentBase):
    """Payment registration payload with optional auto-allocation to specific invoice."""

    invoice_id: int | None = None  # If provided, immediately allocate up to payment amount


class PaymentResponse(PaymentBase):
    """Payment representation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_reference: str
    status: str
    amount_allocated: Decimal
    unallocated_balance: Decimal
    created_at: datetime
    updated_at: datetime


class PaymentDetailResponse(PaymentResponse):
    """Payment detail response including historical allocation ledger entries."""

    allocations: list[PaymentAllocationResponse] = Field(default_factory=list)
