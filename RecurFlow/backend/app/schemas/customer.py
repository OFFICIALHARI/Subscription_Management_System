"""Customer Pydantic v2 schemas aligned with the customers ORM model."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class CustomerBase(BaseModel):
    """Base customer fields matching the customers table."""

    company_name: str = Field(..., min_length=1, max_length=255)
    contact_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = None
    tax_identifier: str | None = None
    billing_address_line1: str = Field(..., min_length=1, max_length=255)
    billing_address_line2: str | None = None
    billing_city: str = Field(..., min_length=1, max_length=100)
    billing_state: str = Field(..., min_length=1, max_length=100)
    billing_postal_code: str = Field(..., min_length=1, max_length=30)
    billing_country: str = "India"


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
    billing_city: str | None = None
    billing_state: str | None = None
    billing_postal_code: str | None = None
    billing_country: str | None = None
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
    """Customer detailed response including related summary metrics."""

    active_subscriptions_count: int = 0
    total_invoiced_amount: float = 0.0
    outstanding_balance: float = 0.0
