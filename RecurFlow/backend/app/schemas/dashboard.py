"""Dashboard analytics and metrics Pydantic v2 schemas."""

from decimal import Decimal

from pydantic import BaseModel, Field


class DashboardKPIsResponse(BaseModel):
    """Real-time financial and operational KPIs calculated from database."""

    mrr: Decimal = Decimal("0.00")
    arr: Decimal = Decimal("0.00")
    total_invoiced: Decimal = Decimal("0.00")
    total_collected: Decimal = Decimal("0.00")
    outstanding_receivables: Decimal = Decimal("0.00")
    overdue_amount: Decimal = Decimal("0.00")
    active_subscriptions: int = 0
    paused_subscriptions: int = 0
    total_customers: int = 0
    unallocated_cash: Decimal = Decimal("0.00")


class MonthlyRevenueItem(BaseModel):
    """Monthly revenue metrics point for chart rendering."""

    month: str  # Format: "YYYY-MM" or "Jan 2026"
    invoiced_amount: Decimal
    collected_amount: Decimal


class RevenueTrendResponse(BaseModel):
    """Historical revenue trend data for charts."""

    trend: list[MonthlyRevenueItem] = Field(default_factory=list)
