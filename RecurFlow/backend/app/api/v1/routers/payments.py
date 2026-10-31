"""Payment recording and allocation API endpoints."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_roles
from app.models.customer import Customer
from app.models.payment import Payment
from app.models.user import User
from app.schemas.payment import (
    PaymentAllocationCreate,
    PaymentAllocationResponse,
    PaymentCreate,
    PaymentDetailResponse,
    PaymentResponse,
)
from app.services.payment_service import payment_service

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("", response_model=list[PaymentResponse])
def list_payments(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    customer_id: Annotated[int | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Payment]:
    """List payments. Customer portal users see only their own payment history."""
    if current_user.role == "CUSTOMER":
        cust = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not cust:
            return []
        customer_id = cust.id
    return payment_service.list_payments(db, customer_id=customer_id, skip=skip, limit=limit)


@router.post(
    "",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def create_payment(
    payment_in: PaymentCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Payment:
    """Register a received payment with optional immediate invoice allocation."""
    return payment_service.create_payment(db, payment_in)


@router.get("/{payment_id}", response_model=PaymentDetailResponse)
def get_payment(
    payment_id: int,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> Payment:
    """Get payment detail with allocation ledger entries."""
    return payment_service.get_payment(db, payment_id)


@router.post(
    "/{payment_id}/allocate",
    response_model=PaymentAllocationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def allocate_payment(
    payment_id: int,
    allocation_in: PaymentAllocationCreate,
    db: Annotated[Session, Depends(get_db)],
) -> object:
    """Allocate a portion of payment to a specific invoice balance."""
    return payment_service.allocate_payment(
        db=db,
        payment_id=payment_id,
        invoice_id=allocation_in.invoice_id,
        amount=Decimal(str(allocation_in.amount)),
    )
