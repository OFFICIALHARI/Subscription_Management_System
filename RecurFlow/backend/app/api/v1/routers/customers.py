"""Customer management API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_roles
from app.models.customer import Customer
from app.models.user import User
from app.schemas.customer import (
    CustomerCreate,
    CustomerDetailResponse,
    CustomerResponse,
    CustomerUpdate,
)
from app.services.customer_service import customer_service

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=list[CustomerResponse])
def list_customers(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    search: Annotated[str | None, Query(description="Search by name or email")] = None,
    is_active: Annotated[bool | None, Query()] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Customer]:
    """List customers with optional search and active filtering."""
    if current_user.role == "CUSTOMER":
        cust = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        return [cust] if cust else []
    return customer_service.list_customers(
        db=db, search=search, is_active=is_active, skip=skip, limit=limit
    )


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def create_customer(
    customer_in: CustomerCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Customer:
    """Create a new customer (Admin or Staff)."""
    return customer_service.create_customer(db, customer_in)


@router.get("/{customer_id}", response_model=CustomerDetailResponse)
def get_customer(
    customer_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CustomerDetailResponse:
    """Get customer details and aggregate metrics."""
    if current_user.role == "CUSTOMER":
        cust = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not cust or cust.id != customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access to another customer's record is denied.",
            )
    return customer_service.get_customer_detail(db, customer_id)


@router.patch(
    "/{customer_id}",
    response_model=CustomerResponse,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def update_customer(
    customer_id: int,
    customer_in: CustomerUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> Customer:
    """Update customer record."""
    return customer_service.update_customer(db, customer_id, customer_in)


@router.delete(
    "/{customer_id}",
    response_model=CustomerResponse,
    dependencies=[Depends(require_roles(["ADMIN"]))],
)
def delete_customer(
    customer_id: int,
    db: Annotated[Session, Depends(get_db)],
) -> Customer:
    """Soft-deactivate customer (Admin only)."""
    return customer_service.delete_customer(db, customer_id)
