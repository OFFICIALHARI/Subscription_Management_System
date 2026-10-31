"""Tax Rate Pydantic v2 schemas aligned with the tax_rates ORM model."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TaxRateBase(BaseModel):
    """Base tax rate fields matching the tax_rates table."""

    name: str = Field(..., min_length=1, max_length=100)
    rate_percentage: Decimal = Field(..., ge=0, le=100)
    tax_type: str = Field(default="EXCLUSIVE", pattern="^(EXCLUSIVE|INCLUSIVE)$")
    description: str | None = None
    is_active: bool = True


class TaxRateCreate(TaxRateBase):
    """Tax rate creation payload."""

    pass


class TaxRateResponse(TaxRateBase):
    """Tax rate representation response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    updated_at: datetime
