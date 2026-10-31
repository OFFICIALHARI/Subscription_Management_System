"""Subscription lifecycle API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_roles
from app.models.customer import Customer
from app.models.subscription import Subscription
from app.models.user import User
from app.schemas.subscription import (
    SubscriptionCloseRequest,
    SubscriptionDetailResponse,
    SubscriptionPauseRequest,
    SubscriptionRenewRequest,
    SubscriptionResponse,
    SubscriptionResumeRequest,
)
from app.services.subscription_service import subscription_service

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])


@router.get("", response_model=list[SubscriptionResponse])
def list_subscriptions(
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    customer_id: Annotated[int | None, Query()] = None,
    status_filter: Annotated[str | None, Query(alias="status")] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Subscription]:
    """List subscriptions with customer isolation."""
    if current_user.role == "CUSTOMER":
        cust = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not cust:
            return []
        customer_id = cust.id
    return subscription_service.list_subscriptions(
        db=db,
        customer_id=customer_id,
        status_filter=status_filter,
        skip=skip,
        limit=limit,
    )


@router.get("/{subscription_id}", response_model=SubscriptionDetailResponse)
def get_subscription(
    subscription_id: int,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> Subscription:
    """Get subscription detail with lines and audit event history."""
    sub = subscription_service.get_subscription(db, subscription_id)
    if current_user.role == "CUSTOMER":
        cust = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not cust or cust.id != sub.customer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this subscription.",
            )
    return sub


@router.post(
    "/{subscription_id}/pause",
    response_model=SubscriptionResponse,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def pause_subscription(
    subscription_id: int,
    pause_in: SubscriptionPauseRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Subscription:
    """Pause an active subscription."""
    return subscription_service.pause_subscription(db, subscription_id, reason=pause_in.reason)


@router.post(
    "/{subscription_id}/resume",
    response_model=SubscriptionResponse,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def resume_subscription(
    subscription_id: int,
    resume_in: SubscriptionResumeRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Subscription:
    """Resume a paused subscription."""
    return subscription_service.resume_subscription(db, subscription_id, notes=resume_in.notes)


@router.post(
    "/{subscription_id}/renew",
    response_model=SubscriptionResponse,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def renew_subscription(
    subscription_id: int,
    renew_in: SubscriptionRenewRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Subscription:
    """Manually renew / extend subscription billing period."""
    return subscription_service.renew_subscription(db, subscription_id, notes=renew_in.notes)


@router.post(
    "/{subscription_id}/close",
    response_model=SubscriptionResponse,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def close_subscription(
    subscription_id: int,
    close_in: SubscriptionCloseRequest,
    db: Annotated[Session, Depends(get_db)],
) -> Subscription:
    """Cancel and close subscription."""
    return subscription_service.close_subscription(db, subscription_id, reason=close_in.reason)
