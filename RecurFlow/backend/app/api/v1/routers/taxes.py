"""Tax rates API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_roles
from app.models.tax import TaxRate
from app.models.user import User
from app.schemas.tax import TaxRateCreate, TaxRateResponse
from app.services.catalogue_service import catalogue_service

router = APIRouter(prefix="/taxes", tags=["Taxes"])


@router.get("", response_model=list[TaxRateResponse])
def list_tax_rates(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    is_active: Annotated[bool | None, Query()] = None,
) -> list[TaxRate]:
    """List available tax rates."""
    return catalogue_service.list_tax_rates(db, is_active=is_active)


@router.post(
    "",
    response_model=TaxRateResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def create_tax_rate(
    tax_in: TaxRateCreate,
    db: Annotated[Session, Depends(get_db)],
) -> TaxRate:
    """Create a new tax rate."""
    return catalogue_service.create_tax_rate(db, tax_in)
