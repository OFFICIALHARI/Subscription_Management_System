"""Subscription Plan catalogue API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user, get_db, require_roles
from app.models.plan import Plan
from app.models.user import User
from app.schemas.catalogue import PlanCreate, PlanResponse, PlanUpdate
from app.services.catalogue_service import catalogue_service

router = APIRouter(prefix="/plans", tags=["Plans"])


@router.get("", response_model=list[PlanResponse])
def list_plans(
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
    is_active: Annotated[bool | None, Query()] = None,
) -> list[Plan]:
    """List billing plans (Daily, Weekly, Monthly, Yearly)."""
    return catalogue_service.list_plans(db, is_active=is_active)


@router.post(
    "",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def create_plan(
    plan_in: PlanCreate,
    db: Annotated[Session, Depends(get_db)],
) -> Plan:
    """Create a new billing plan with interval specification."""
    return catalogue_service.create_plan(db, plan_in)


@router.get("/{plan_id}", response_model=PlanResponse)
def get_plan(
    plan_id: int,
    db: Annotated[Session, Depends(get_db)],
    _user: Annotated[User, Depends(get_current_user)],
) -> Plan:
    """Get plan by ID."""
    return catalogue_service.get_plan(db, plan_id)


@router.patch(
    "/{plan_id}",
    response_model=PlanResponse,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def update_plan(
    plan_id: int,
    plan_in: PlanUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> Plan:
    """Update plan details."""
    return catalogue_service.update_plan(db, plan_id, plan_in)
