"""Customer Pydantic v2 schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class CustomerBase(BaseModel):
    """Base customer fields."""

    company_name: str
    contact_name: str
    email: EmailStr
    phone: str | None = None
    tax_identifier: str | None = None
    billing_address_line1: str
    billing_address_line2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str = "US"
    currency: str = "USD"
    payment_terms_days: int = 30


class CustomerCreate(CustomerBase):
    """Customer creation payload."""

    user_id: int | None = None


class CustomerUpdate(BaseModel):
    """Customer update payload."""

    company_name: str | None = None
    contact_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    tax_identifier: str | None = None
    billing_address_line1: str | None = None
    billing_address_line2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    currency: str | None = None
    payment_terms_days: int | None = None
    is_active: bool | None = None


class CustomerResponse(CustomerBase):
    """Customer representation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CustomerDetailResponse(CustomerResponse):
    """Customer detailed response including counts or related summary."""

    active_subscriptions_count: int = 0
    total_invoiced_amount: float = 0.0
    outstanding_balance: float = 0.0
