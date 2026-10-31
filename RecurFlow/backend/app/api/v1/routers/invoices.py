"""Invoice management API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_current_user, get_db
from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.user import User
from app.schemas.invoice import InvoiceDetailResponse, InvoiceResponse
from app.services.customer_service import customer_service

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("", response_model=list[InvoiceResponse])
def list_invoices(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    customer_id: Annotated[int | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Invoice]:
    """List invoices. Customer portal users see only their own invoices."""
    query = db.query(Invoice)
    if current_user.role == "CUSTOMER":
        cust = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not cust:
            return []
        query = query.filter(Invoice.customer_id == cust.id)
    elif customer_id:
        query = query.filter(Invoice.customer_id == customer_id)

    if status_filter:
        query = query.filter(Invoice.status == status_filter.upper())

    return (
        query.order_by(Invoice.invoice_date.desc(), Invoice.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{invoice_id}", response_model=InvoiceDetailResponse)
def get_invoice(
    invoice_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Invoice:
    """Get invoice detail with line items."""
    invoice = (
        db.query(Invoice)
        .options(joinedload(Invoice.lines))
        .filter(Invoice.id == invoice_id)
        .first()
    )
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found.",
        )
    if current_user.role == "CUSTOMER":
        cust = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not cust or cust.id != invoice.customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this invoice.",
            )
    return invoice
