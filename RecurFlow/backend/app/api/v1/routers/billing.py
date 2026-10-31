"""Billing cycle execution and preview API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db, require_roles
from app.schemas.billing import (
    BillingPreviewResponse,
    BillingRunRequest,
    BillingRunResponse,
)
from app.services.billing_service import billing_service

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get(
    "/preview",
    response_model=BillingPreviewResponse,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def preview_billing(
    db: Annotated[Session, Depends(get_db)],
    run_date: str | None = None,
) -> BillingPreviewResponse:
    """Preview subscriptions due for billing on a given date (defaults to today)."""
    from datetime import date

    target = date.fromisoformat(run_date) if run_date else None
    return billing_service.preview_due_subscriptions(db, run_date=target)


@router.post(
    "/run",
    response_model=BillingRunResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def run_billing(
    billing_in: BillingRunRequest,
    db: Annotated[Session, Depends(get_db)],
) -> BillingRunResponse:
    """
    Execute recurring billing cycle.
    Generates invoices for all active subscriptions due on or before run_date.
    Idempotent: duplicate runs for same period are skipped automatically.
    """
    return billing_service.execute_billing_run(
        db, run_date=billing_in.run_date, auto_post=billing_in.auto_post
    )
