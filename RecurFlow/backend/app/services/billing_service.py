"""Recurring billing cycle execution, invoice generation, and idempotency protection."""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.customer import Customer
from app.models.invoice import Invoice, InvoiceLine
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

    def preview_due_subscriptions(
        self, db: Session, run_date: date | None = None
    ) -> BillingPreviewResponse:
        """Inspect all subscriptions that are due for invoice generation on or before run_date."""
        target_date = run_date or date.today()

        due_subs = (
            db.query(Subscription)
            .options(joinedload(Subscription.lines))
            .filter(
                Subscription.status == "ACTIVE",
                Subscription.next_billing_date <= target_date,
            )
            .all()
        )

        preview_items: list[BillingPreviewItem] = []
        total_revenue = Decimal("0.00")

        for sub in due_subs:
            cust = db.query(Customer).filter(Customer.id == sub.customer_id).first()
            cust_name = cust.company_name if cust else "Unknown Customer"
            est_amount = sub.total_recurring_amount

            preview_items.append(
                BillingPreviewItem(
                    subscription_id=sub.id,
                    subscription_number=sub.subscription_number,
                    customer_id=sub.customer_id,
                    customer_name=cust_name,
                    billing_interval=sub.billing_interval,
                    period_start=sub.current_period_start,
                    period_end=sub.current_period_end,
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
        Executes recurring billing cycle for all active subscriptions due on or before run_date.
        Enforces idempotency: never generates duplicate invoices for same subscription and period.
        """
        target_date = run_date or date.today()

        due_subs = (
            db.query(Subscription)
            .options(joinedload(Subscription.lines))
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
            p_start = sub.current_period_start
            p_end = sub.current_period_end

            # Idempotency check: does an invoice already exist for this (subscription_id, period_start, period_end)?
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
                # Idempotent skip: prevent duplicate billing
                invoices_skipped += 1
                continue

            cust = db.query(Customer).filter(Customer.id == sub.customer_id).first()
            payment_terms = cust.payment_terms_days if cust else 30
            due_date = target_date + timedelta(days=payment_terms)

            inv_number = self._generate_invoice_number(db)
            invoice_status = "ISSUED" if auto_post else "DRAFT"

            invoice = Invoice(
                invoice_number=inv_number,
                customer_id=sub.customer_id,
                subscription_id=sub.id,
                status=invoice_status,
                currency=sub.currency,
                billing_period_start=p_start,
                billing_period_end=p_end,
                invoice_date=target_date,
                due_date=due_date,
                notes=f"Recurring billing for {sub.subscription_number} ({p_start} to {p_end})",
            )
            db.add(invoice)
            db.flush()

            # Copy line items
            sub_total = Decimal("0.00")
            sub_discount = Decimal("0.00")
            sub_tax = Decimal("0.00")

            for s_line in sub.lines:
                inv_line = InvoiceLine(
                    invoice_id=invoice.id,
                    product_id=s_line.product_id,
                    variant_id=s_line.variant_id,
                    subscription_line_id=s_line.id,
                    description=s_line.description,
                    quantity=s_line.quantity,
                    unit_price=s_line.unit_price,
                    discount_amount=s_line.discount_amount,
                    subtotal=s_line.subtotal,
                    tax_rate_id=s_line.tax_rate_id,
                    tax_amount=s_line.tax_amount,
                    total_amount=s_line.total_amount,
                )
                db.add(inv_line)
                sub_total += s_line.subtotal
                sub_discount += s_line.discount_amount
                sub_tax += s_line.tax_amount

            invoice.subtotal = round_currency(sub_total)
            invoice.discount_amount = round_currency(sub_discount)
            invoice.tax_amount = round_currency(sub_tax)
            line_sum = round_currency(sub_total - sub_discount + sub_tax)
            invoice.total_amount = line_sum
            invoice.amount_paid = Decimal("0.00")
            invoice.balance_due = line_sum

            # Advance subscription to next period using billing_date_service
            next_date = billing_date_service.calculate_next_billing_date(
                current_date=p_end,
                interval=sub.billing_interval,
                interval_count=sub.interval_count,
                anchor_day=sub.billing_anchor_day,
                anchor_month=sub.billing_anchor_month,
            )
            sub.current_period_start = p_end
            sub.current_period_end = next_date
            sub.next_billing_date = next_date

            # Log subscription billed event
            event = SubscriptionEvent(
                subscription_id=sub.id,
                event_type="BILLED",
                from_status=sub.status,
                to_status=sub.status,
                description=f"Generated invoice {inv_number} for period {p_start} to {p_end}.",
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
