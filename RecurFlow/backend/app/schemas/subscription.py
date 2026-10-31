"""Subscription and SubscriptionLine Pydantic v2 schemas."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class SubscriptionLineResponse(BaseModel):
    """Subscription line representation response (matches SubscriptionLine ORM model)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_id: int
    product_id: int
    product_variant_id: int | None = None
    quotation_line_id: int | None = None
    description_snapshot: str
    quantity: int
    unit_price_snapshot: Decimal
    tax_rate_id: int | None = None
    tax_rate_snapshot: Decimal


class SubscriptionEventResponse(BaseModel):
    """Subscription lifecycle event representation."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_id: int
    event_type: str
    from_status: str | None
    to_status: str
    reason: str | None
    created_at: datetime


class SubscriptionResponse(BaseModel):
    """Subscription summary response (matches Subscription ORM model)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_number: str
    customer_id: int
    plan_id: int
    status: str
    billing_anchor_day: int
    start_date: date
    next_billing_date: date
    end_date: date | None = None
    currency: str
    recurring_amount: Decimal
    paused_at: datetime | None = None
    resumed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SubscriptionDetailResponse(SubscriptionResponse):
    """Subscription detail including line items and audit timeline."""

    lines: list[SubscriptionLineResponse] = Field(default_factory=list)
    events: list[SubscriptionEventResponse] = Field(default_factory=list)


class SubscriptionPauseRequest(BaseModel):
    """Request to pause an active subscription."""

    reason: str | None = None


class SubscriptionResumeRequest(BaseModel):
    """Request to resume a paused subscription."""

    notes: str | None = None


class SubscriptionRenewRequest(BaseModel):
    """Request to manually renew or extend subscription."""

    notes: str | None = None


class SubscriptionCloseRequest(BaseModel):
    """Request to cancel/close a subscription."""

    reason: str
