"""Discount coupons and promotions API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_roles
from app.models.discount import Discount
from app.models.user import User
from app.schemas.discount import (
    DiscountCreate,
    DiscountResponse,
    DiscountValidationRequest,
    DiscountValidationResponse,
)
from app.services.discount_service import discount_service

router = APIRouter(prefix="/discounts", tags=["Discounts"])


@router.get("", response_model=list[DiscountResponse])
def list_discounts(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    is_active: Annotated[bool | None, Query()] = None,
) -> list[Discount]:
    """List discount coupons."""
    return discount_service.list_discounts(db, is_active=is_active)


@router.post(
    "",
    response_model=DiscountResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def create_discount(
    discount_in: DiscountCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Discount:
    """Create a new discount or promotional coupon."""
    return discount_service.create_discount(db, discount_in)


@router.post("/validate", response_model=DiscountValidationResponse)
def validate_discount(
    validation_in: DiscountValidationRequest,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> DiscountValidationResponse:
    """Validate coupon code eligibility against order amount."""
    return discount_service.validate_code(
        db, code=validation_in.code, order_amount=validation_in.order_amount
    )
