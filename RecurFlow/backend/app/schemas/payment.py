"""Payment Pydantic v2 schemas aligned with payments and payment_allocations."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, computed_field


class PaymentAllocationCreate(BaseModel):
    """Payload to allocate an existing payment to an invoice."""

    invoice_id: int
    amount: Decimal = Field(..., gt=0)


class PaymentAllocationResponse(BaseModel):
    """Payment allocation record matching payment_allocations."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_id: int
    invoice_id: int
    allocated_amount: Decimal
    allocated_at: datetime


class PaymentBase(BaseModel):
    """Base payment fields matching payments."""

    customer_id: int
    amount: Decimal = Field(..., gt=0)
    currency: str = "USD"
    payment_method: str = "BANK_TRANSFER"
    paid_at: date | None = None
    transaction_reference: str | None = None
    notes: str | None = None


class PaymentCreate(PaymentBase):
    """Payment registration payload with optional immediate invoice allocation."""

    invoice_id: int | None = None


class PaymentResponse(PaymentBase):
    """Payment representation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    payment_number: str
    status: str
    amount_allocated: Decimal
    created_at: datetime
    updated_at: datetime

    @computed_field  # type: ignore[prop-decorator]
    @property
    def unallocated_balance(self) -> Decimal:
        return (self.amount - self.amount_allocated).quantize(Decimal("0.01"))


class PaymentDetailResponse(PaymentResponse):
    """Payment detail including allocation ledger entries."""

    allocations: list[PaymentAllocationResponse] = Field(default_factory=list)
