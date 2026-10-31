"""Tax Rate Pydantic v2 schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class TaxRateBase(BaseModel):
    """Base tax rate fields."""

    code: str
    name: str
    rate_percent: Decimal = Field(..., ge=0, le=100)
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
