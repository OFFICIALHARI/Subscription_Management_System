"""Financial dashboard analytics API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import get_db, require_roles
from app.schemas.dashboard import DashboardKPIsResponse, RevenueTrendResponse
from app.services.dashboard_service import dashboard_service
from sqlalchemy.orm import Session

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/kpis",
    response_model=DashboardKPIsResponse,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def get_dashboard_kpis(
    db: Annotated[Session, Depends(get_db)],
) -> DashboardKPIsResponse:
    """
    Live financial and operational KPIs:
    MRR, ARR, Total Invoiced, Total Collected, Outstanding Receivables,
    Overdue Amount, Active/Paused Subscriptions, Customers, Unallocated Cash.
    """
    return dashboard_service.get_kpis(db)


@router.get(
    "/revenue-trend",
    response_model=RevenueTrendResponse,
    dependencies=[Depends(require_roles(["ADMIN", "STAFF"]))],
)
def get_revenue_trend(
    db: Annotated[Session, Depends(get_db)],
) -> RevenueTrendResponse:
    """Monthly historical trend of invoiced vs collected revenue for charting."""
    return dashboard_service.get_revenue_trend(db)
