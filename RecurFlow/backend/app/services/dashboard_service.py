"""Financial dashboard metrics and revenue analytics service."""

from datetime import date
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.payment import Payment, PaymentAllocation
from app.models.subscription import Subscription
from app.schemas.dashboard import DashboardKPIsResponse, MonthlyRevenueItem, RevenueTrendResponse
from app.services.pricing_service import round_currency


class DashboardService:
    """Calculates live subscription metrics, MRR, ARR, and financial reconciliation from database."""

    def get_kpis(self, db: Session) -> DashboardKPIsResponse:
        """Compute real-time KPI metrics."""
        today = date.today()

        # 1. Active Subscriptions and MRR calculation
        active_subs = (
            db.query(Subscription)
            .filter(Subscription.status == "ACTIVE")
            .all()
        )

        mrr_total = Decimal("0.00")
        for sub in active_subs:
            amount = sub.total_recurring_amount
            interval = sub.billing_interval.upper()
            count = max(sub.interval_count, 1)

            if interval == "DAILY":
                monthly_val = (amount * Decimal("30.00")) / Decimal(count)
            elif interval == "WEEKLY":
                monthly_val = (amount * Decimal("4.333333")) / Decimal(count)
            elif interval == "MONTHLY":
                monthly_val = amount / Decimal(count)
            elif interval == "YEARLY":
                monthly_val = amount / (Decimal("12.00") * Decimal(count))
            else:
                monthly_val = amount

            mrr_total += monthly_val

        mrr = round_currency(mrr_total)
        arr = round_currency(mrr * Decimal("12.00"))

        # 2. Subscription counts
        active_sub_count = len(active_subs)
        paused_sub_count = (
            db.query(func.count(Subscription.id))
            .filter(Subscription.status == "PAUSED")
            .scalar()
            or 0
        )

        # 3. Customer count
        total_customers = (
            db.query(func.count(Customer.id))
            .filter(Customer.is_active == True)  # noqa: E712
            .scalar()
            or 0
        )

        # 4. Invoiced and Receivables
        invoiced_sum = (
            db.query(func.coalesce(func.sum(Invoice.total_amount), Decimal("0.00")))
            .filter(Invoice.status != "CANCELLED")
            .scalar()
        )
        total_invoiced = round_currency(Decimal(str(invoiced_sum)))

        receivables_sum = (
            db.query(func.coalesce(func.sum(Invoice.balance_due), Decimal("0.00")))
            .filter(Invoice.status.in_(["ISSUED", "PARTIALLY_PAID", "OVERDUE"]))
            .scalar()
        )
        outstanding_receivables = round_currency(Decimal(str(receivables_sum)))

        overdue_sum = (
            db.query(func.coalesce(func.sum(Invoice.balance_due), Decimal("0.00")))
            .filter(
                Invoice.status != "CANCELLED",
                Invoice.balance_due > 0,
                (Invoice.status == "OVERDUE") | (Invoice.due_date < today),
            )
            .scalar()
        )
        overdue_amount = round_currency(Decimal(str(overdue_sum)))

        # 5. Collected payments (sum of allocations)
        collected_sum = (
            db.query(func.coalesce(func.sum(PaymentAllocation.allocated_amount), Decimal("0.00")))
            .filter(PaymentAllocation.reversed_at.is_(None))
            .scalar()
        )
        total_collected = round_currency(Decimal(str(collected_sum)))

        # 6. Unallocated cash
        unallocated_sum = (
            db.query(func.coalesce(func.sum(Payment.unallocated_balance), Decimal("0.00")))
            .filter(Payment.status == "COMPLETED")
            .scalar()
        )
        unallocated_cash = round_currency(Decimal(str(unallocated_sum)))

        return DashboardKPIsResponse(
            mrr=mrr,
            arr=arr,
            total_invoiced=total_invoiced,
            total_collected=total_collected,
            outstanding_receivables=outstanding_receivables,
            overdue_amount=overdue_amount,
            active_subscriptions=active_sub_count,
            paused_subscriptions=paused_sub_count,
            total_customers=total_customers,
            unallocated_cash=unallocated_cash,
        )

    def get_revenue_trend(self, db: Session) -> RevenueTrendResponse:
        """Monthly historical aggregated trend of invoiced vs collected revenue."""
        # Query monthly invoiced
        invoiced_rows = (
            db.query(
                func.to_char(Invoice.invoice_date, "YYYY-MM").label("month"),
                func.sum(Invoice.total_amount).label("invoiced"),
            )
            .filter(Invoice.status != "CANCELLED")
            .group_by("month")
            .order_by("month")
            .all()
        )

        invoiced_map = {row.month: Decimal(str(row.invoiced)) for row in invoiced_rows}

        # Query monthly collected
        collected_rows = (
            db.query(
                func.to_char(PaymentAllocation.allocation_date, "YYYY-MM").label("month"),
                func.sum(PaymentAllocation.allocated_amount).label("collected"),
            )
            .filter(PaymentAllocation.reversed_at.is_(None))
            .group_by("month")
            .order_by("month")
            .all()
        )

        collected_map = {row.month: Decimal(str(row.collected)) for row in collected_rows}

        all_months = sorted(set(list(invoiced_map.keys()) + list(collected_map.keys())))
        trend: list[MonthlyRevenueItem] = []

        for m in all_months:
            trend.append(
                MonthlyRevenueItem(
                    month=m,
                    invoiced_amount=round_currency(invoiced_map.get(m, Decimal("0.00"))),
                    collected_amount=round_currency(collected_map.get(m, Decimal("0.00"))),
                )
            )

        return RevenueTrendResponse(trend=trend)


dashboard_service = DashboardService()
