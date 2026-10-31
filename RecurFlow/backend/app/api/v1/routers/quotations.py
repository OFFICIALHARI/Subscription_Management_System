"""Quotation API endpoints and subscription conversion."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_roles
from app.models.customer import Customer
from app.models.quotation import Quotation
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.quotation import (
    QuotationCreate,
    QuotationDetailResponse,
    QuotationResponse,
)
from app.schemas.subscription import SubscriptionResponse
from app.services.quotation_service import quotation_service

router = APIRouter(prefix="/quotations", tags=["Quotations"])


@router.get("", response_model=list[QuotationResponse])
def list_quotations(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    customer_id: Annotated[int | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Quotation]:
    """List quotations with customer isolation for customer portal users."""
    if current_user.role == "CUSTOMER":
        cust = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not cust:
            return []
        customer_id = cust.id
    return quotation_service.list_quotations(
        db=db,
        customer_id=customer_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )


@router.post(
    "",
    response_model=QuotationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def create_quotation(
    quote_in: QuotationCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Quotation:
    """Create a new quotation draft."""
    return quotation_service.create_quotation(db, quote_in)


@router.get("/{quotation_id}", response_model=QuotationDetailResponse)
def get_quotation(
    quotation_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Quotation:
    """Get quotation details and line items."""
    quote = quotation_service.get_quotation(db, quotation_id)
    if current_user.role == "CUSTOMER":
        cust = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not cust or cust.id != quote.customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this quotation.",
            )
    return quote


@router.post(
    "/{quotation_id}/confirm",
    response_model=QuotationResponse,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def confirm_quotation(
    quotation_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> Quotation:
    """Confirm a quotation before conversion."""
    return quotation_service.confirm_quotation(db, quotation_id)


@router.post(
    "/{quotation_id}/convert",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def convert_quotation(
    quotation_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> Subscription:
    """Atomically convert a quotation to an active subscription with line items and billing cycle."""
    return quotation_service.convert_to_subscription(db, quotation_id)
