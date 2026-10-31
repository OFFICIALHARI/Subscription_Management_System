"""Recurring billing cycle execution, invoice generation, and idempotency protection."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceLine
from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionEvent
from app.schemas.billing import (
    BillingPreviewItem,
    BillingPreviewResponse,
    BillingRunResponse,
)
from app.services.billing_date_service import billing_date_service
from app.services.pricing_service import calculate_line_totals, round_currency


class BillingService:
    """Manages batch billing runs, previewing due subscriptions, and idempotent invoice creation."""

    def _generate_invoice_number(self, db: Session) -> str:
        current_year = date.today().year
        count = (
            db.query(func.count(Invoice.id))
            .filter(Invoice.invoice_number.like(f"INV-{current_year}-%"))
            .scalar()
            or 0
        )
        return f"INV-{current_year}-{count + 1:05d}"

    def _period_for(self, sub: Subscription, plan: Plan) -> tuple[date, date]:
        period_end = sub.next_billing_date
        period_start, computed_end = billing_date_service.compute_billing_period(
            period_start=sub.start_date,
            interval=plan.billing_interval,  # type: ignore[arg-type]
            interval_count=plan.interval_count,
            anchor_day=sub.billing_anchor_day,
        )
        # Walk forward from start until the window that ends on next_billing_date.
        cursor = period_start
        window_end = computed_end
        guard = 0
        while window_end < period_end and guard < 240:
            cursor = window_end
            window_end = billing_date_service.calculate_next_billing_date(
                current_date=cursor,
                interval=plan.billing_interval,  # type: ignore[arg-type]
                interval_count=plan.interval_count,
                anchor_day=sub.billing_anchor_day,
                anchor_month=sub.start_date.month,
            )
            guard += 1
        return cursor, period_end

    def preview_due_subscriptions(
        self, db: Session, run_date: date | None = None
    ) -> BillingPreviewResponse:
        """Inspect all subscriptions that are due for invoice generation on or before run_date."""
        target_date = run_date or date.today()

        due_subs = (
            db.query(Subscription)
            .options(joinedload(Subscription.lines), joinedload(Subscription.plan))
            .filter(
                Subscription.status == "ACTIVE",
                Subscription.next_billing_date <= target_date,
            )
            .all()
        )

        preview_items: list[BillingPreviewItem] = []
        total_revenue = Decimal("0.00")

        for sub in due_subs:
            plan = sub.plan or db.query(Plan).filter(Plan.id == sub.plan_id).first()
            if not plan:
                continue
            cust = db.query(Customer).filter(Customer.id == sub.customer_id).first()
            cust_name = cust.company_name if cust else "Unknown Customer"
            p_start, p_end = self._period_for(sub, plan)
            est_amount = sub.recurring_amount

            preview_items.append(
                BillingPreviewItem(
                    subscription_id=sub.id,
                    subscription_number=sub.subscription_number,
                    customer_id=sub.customer_id,
                    customer_name=cust_name,
                    billing_interval=plan.billing_interval,
                    period_start=p_start,
                    period_end=p_end,
                    estimated_amount=est_amount,
                    currency=sub.currency,
                )
            )
            total_revenue += est_amount

        return BillingPreviewResponse(
            run_date=target_date,
            total_due_count=len(preview_items),
            total_estimated_revenue=round_currency(total_revenue),
            items=preview_items,
        )

    def execute_billing_run(
        self, db: Session, run_date: date | None = None, auto_post: bool = True
    ) -> BillingRunResponse:
        """
        Execute recurring billing for active subscriptions due on or before run_date.
        Idempotent: never generates duplicate invoices for the same subscription and period.
        """
        target_date = run_date or date.today()

        due_subs = (
            db.query(Subscription)
            .options(joinedload(Subscription.lines), joinedload(Subscription.plan))
            .filter(
                Subscription.status == "ACTIVE",
                Subscription.next_billing_date <= target_date,
            )
            .all()
        )

        invoices_generated = 0
        invoices_skipped = 0
        total_invoiced = Decimal("0.00")
        generated_ids: list[int] = []

        for sub in due_subs:
            plan = sub.plan or db.query(Plan).filter(Plan.id == sub.plan_id).first()
            if not plan:
                invoices_skipped += 1
                continue

            p_start, p_end = self._period_for(sub, plan)

            existing_invoice = (
                db.query(Invoice)
                .filter(
                    Invoice.subscription_id == sub.id,
                    Invoice.billing_period_start == p_start,
                    Invoice.billing_period_end == p_end,
                )
                .first()
            )
            if existing_invoice:
                invoices_skipped += 1
                continue

            cust = db.query(Customer).filter(Customer.id == sub.customer_id).first()
            payment_terms = sub.payment_terms_days if sub.payment_terms_days else 15
            due_date = target_date + timedelta(days=payment_terms)
            if due_date < target_date:
                due_date = target_date

            invoice_status = "CONFIRMED" if auto_post else "DRAFT"
            invoice = Invoice(
                invoice_number=self._generate_invoice_number(db),
                customer_id=sub.customer_id,
                subscription_id=sub.id,
                status=invoice_status,
                currency=sub.currency,
                billing_period_start=p_start,
                billing_period_end=p_end,
                issue_date=target_date,
                due_date=due_date,
                notes=f"Recurring billing for {sub.subscription_number} ({p_start} to {p_end})",
            )
            db.add(invoice)
            db.flush()

            sub_total = Decimal("0.00")
            sub_discount = Decimal("0.00")
            sub_tax = Decimal("0.00")

            lines = list(sub.lines)
            if not lines:
                computed = calculate_line_totals(
                    quantity=1,
                    unit_price=sub.recurring_amount,
                    discount_amount=Decimal("0.00"),
                    tax_rate_percent=Decimal("0.00"),
                )
                db.add(
                    InvoiceLine(
                        invoice_id=invoice.id,
                        subscription_line_id=None,
                        description_snapshot=f"{plan.name} recurring charge",
                        quantity=1,
                        unit_price_snapshot=sub.recurring_amount,
                        discount_amount=Decimal("0.00"),
                        tax_rate_snapshot=Decimal("0.00"),
                        line_subtotal=computed["subtotal"],
                        line_tax=computed["tax_amount"],
                        line_total=computed["total_amount"],
                    )
                )
                sub_total = computed["subtotal"]
                sub_tax = computed["tax_amount"]
            else:
                for s_line in lines:
                    computed = calculate_line_totals(
                        quantity=s_line.quantity,
                        unit_price=s_line.unit_price_snapshot,
                        discount_amount=Decimal("0.00"),
                        tax_rate_percent=s_line.tax_rate_snapshot or Decimal("0.00"),
                    )
                    db.add(
                        InvoiceLine(
                            invoice_id=invoice.id,
                            subscription_line_id=s_line.id,
                            description_snapshot=s_line.description_snapshot,
                            quantity=s_line.quantity,
                            unit_price_snapshot=s_line.unit_price_snapshot,
                            discount_amount=computed["discount_amount"],
                            tax_rate_snapshot=s_line.tax_rate_snapshot,
                            line_subtotal=computed["subtotal"],
                            line_tax=computed["tax_amount"],
                            line_total=computed["total_amount"],
                        )
                    )
                    sub_total += computed["subtotal"]
                    sub_discount += computed["discount_amount"]
                    sub_tax += computed["tax_amount"]

            line_sum = round_currency(sub_total - sub_discount + sub_tax)
            invoice.subtotal = round_currency(sub_total)
            invoice.discount_amount = round_currency(sub_discount)
            invoice.tax_amount = round_currency(sub_tax)
            invoice.total_amount = line_sum
            invoice.amount_paid = Decimal("0.00")
            invoice.balance_due = line_sum

            next_date = billing_date_service.calculate_next_billing_date(
                current_date=p_end,
                interval=plan.billing_interval,  # type: ignore[arg-type]
                interval_count=plan.interval_count,
                anchor_day=sub.billing_anchor_day,
                anchor_month=sub.start_date.month,
            )
            sub.next_billing_date = next_date

            event = SubscriptionEvent(
                subscription_id=sub.id,
                event_type="BILLED",
                from_status=sub.status,
                to_status=sub.status,
                reason=f"Generated invoice {invoice.invoice_number} for period {p_start} to {p_end}.",
            )
            db.add(event)

            invoices_generated += 1
            total_invoiced += line_sum
            generated_ids.append(invoice.id)

        db.commit()

        return BillingRunResponse(
            run_date=target_date,
            invoices_generated=invoices_generated,
            invoices_skipped_idempotent=invoices_skipped,
            total_invoiced_amount=round_currency(total_invoiced),
            generated_invoice_ids=generated_ids,
        )


billing_service = BillingService()
