"""Quotation domain service and atomic conversion to subscription."""

from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.plan import Plan
from app.models.product import Product
from app.models.quotation import Quotation, QuotationLine
from app.models.subscription import Subscription, SubscriptionEvent, SubscriptionLine
from app.models.tax import TaxRate
from app.schemas.quotation import QuotationCreate, QuotationUpdate
from app.services.billing_date_service import billing_date_service
from app.services.discount_service import discount_service
from app.services.pricing_service import calculate_line_totals, round_currency


class QuotationService:
    """Manages quotation drafts, calculations, confirmations, and conversion to active subscriptions."""

    def _generate_quotation_number(self, db: Session) -> str:
        current_year = date.today().year
        count = (
            db.query(func.count(Quotation.id))
            .filter(Quotation.quotation_number.like(f"QUO-{current_year}-%"))
            .scalar()
            or 0
        )
        return f"QUO-{current_year}-{count + 1:05d}"

    def _generate_subscription_number(self, db: Session) -> str:
        current_year = date.today().year
        count = (
            db.query(func.count(Subscription.id))
            .filter(Subscription.subscription_number.like(f"SUB-{current_year}-%"))
            .scalar()
            or 0
        )
        return f"SUB-{current_year}-{count + 1:05d}"

    def list_quotations(
        self,
        db: Session,
        customer_id: int | None = None,
        status_filter: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Quotation]:
        query = db.query(Quotation).options(joinedload(Quotation.lines))
        if customer_id is not None:
            query = query.filter(Quotation.customer_id == customer_id)
        if status_filter:
            query = query.filter(Quotation.status == status_filter.upper())
        return query.order_by(Quotation.created_at.desc()).offset(skip).limit(limit).all()

    def get_quotation(self, db: Session, quotation_id: int) -> Quotation:
        quote = (
            db.query(Quotation)
            .options(joinedload(Quotation.lines))
            .filter(Quotation.id == quotation_id)
            .first()
        )
        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Quotation with ID {quotation_id} not found.",
            )
        return quote

    def create_quotation(self, db: Session, quote_in: QuotationCreate) -> Quotation:
        """Create a quotation, evaluating lines, tax rates, and optional discounts."""
        quote_number = self._generate_quotation_number(db)

        lines_to_add: list[dict] = []
        raw_lines = quote_in.lines

        # If lines not explicitly supplied but plan_id given, pre-fill from plan items
        if not raw_lines and quote_in.plan_id:
            plan = db.query(Plan).options(joinedload(Plan.items)).filter(Plan.id == quote_in.plan_id).first()
            if plan and plan.items:
                for item in plan.items:
                    prod = db.query(Product).filter(Product.id == item.product_id).first()
                    lines_to_add.append({
                        "product_id": item.product_id,
                        "variant_id": item.variant_id,
                        "description": prod.name if prod else "Subscription Line Item",
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "tax_rate_id": prod.tax_rate_id if prod else quote_in.tax_rate_id,
                    })

        for line_in in raw_lines:
            prod = db.query(Product).filter(Product.id == line_in.product_id).first()
            desc = line_in.description or (prod.name if prod else "Product Line")
            tax_id = line_in.tax_rate_id or (prod.tax_rate_id if prod else quote_in.tax_rate_id)
            lines_to_add.append({
                "product_id": line_in.product_id,
                "variant_id": line_in.variant_id,
                "description": desc,
                "quantity": line_in.quantity,
                "unit_price": line_in.unit_price,
                "tax_rate_id": tax_id,
            })

        quotation = Quotation(
            quotation_number=quote_number,
            customer_id=quote_in.customer_id,
            plan_id=quote_in.plan_id,
            status="DRAFT",
            valid_until=quote_in.valid_until,
            currency=quote_in.currency,
            terms_conditions=quote_in.terms_conditions,
            notes=quote_in.notes,
        )
        db.add(quotation)
        db.flush()

        # Compute line totals
        total_subtotal = Decimal("0.00")
        total_tax = Decimal("0.00")

        for line_data in lines_to_add:
            tax_rate_percent = Decimal("0.00")
            if line_data["tax_rate_id"]:
                tax_obj = db.query(TaxRate).filter(TaxRate.id == line_data["tax_rate_id"]).first()
                if tax_obj:
                    tax_rate_percent = tax_obj.rate_percent

            computed = calculate_line_totals(
                quantity=line_data["quantity"],
                unit_price=line_data["unit_price"],
                discount_amount=Decimal("0.00"),
                tax_rate_percent=tax_rate_percent,
            )

            q_line = QuotationLine(
                quotation_id=quotation.id,
                product_id=line_data["product_id"],
                variant_id=line_data["variant_id"],
                description=line_data["description"],
                quantity=line_data["quantity"],
                unit_price=line_data["unit_price"],
                discount_amount=computed["discount_amount"],
                subtotal=computed["subtotal"],
                tax_rate_id=line_data["tax_rate_id"],
                tax_amount=computed["tax_amount"],
                total_amount=computed["total_amount"],
            )
            db.add(q_line)
            total_subtotal += computed["subtotal"]
            total_tax += computed["tax_amount"]

        # Discount code check
        quote_discount_amount = Decimal("0.00")
        if quote_in.discount_code:
            v_res = discount_service.validate_code(db, quote_in.discount_code, total_subtotal)
            if v_res.valid:
                quote_discount_amount = v_res.calculated_discount_amount

        quotation.subtotal = total_subtotal
        quotation.discount_amount = quote_discount_amount
        quotation.tax_amount = total_tax
        quotation.total_amount = round_currency(total_subtotal - quote_discount_amount + total_tax)

        db.commit()
        db.refresh(quotation)
        return quotation

    def confirm_quotation(self, db: Session, quotation_id: int) -> Quotation:
        """Mark quotation as CONFIRMED."""
        quote = self.get_quotation(db, quotation_id)
        if quote.status in ["CANCELLED", "REJECTED", "EXPIRED", "CONVERTED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot confirm quotation in state '{quote.status}'.",
            )
        quote.status = "CONFIRMED"
        db.commit()
        db.refresh(quote)
        return quote

    def convert_to_subscription(self, db: Session, quotation_id: int) -> Subscription:
        """
        Atomically converts a confirmed quotation into an active subscription.
        Copies lines with lineage references, initializes billing dates and anchor.
        """
        quote = self.get_quotation(db, quotation_id)
        if quote.status == "CONVERTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Quotation {quote.quotation_number} has already been converted to subscription ID {quote.converted_subscription_id}.",
            )
        if quote.status != "CONFIRMED":
            # Auto-confirm if still in draft/sent
            quote.status = "CONFIRMED"

        if not quote.lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot convert a quotation with zero line items to a subscription.",
            )

        # Plan billing parameters
        billing_interval = "MONTHLY"
        interval_count = 1
        trial_days = 0
        if quote.plan_id:
            plan = db.query(Plan).filter(Plan.id == quote.plan_id).first()
            if plan:
                billing_interval = plan.billing_interval
                interval_count = plan.interval_count
                trial_days = plan.trial_period_days

        start_date = date.today()
        anchor_day = start_date.day
        anchor_month = start_date.month if billing_interval == "YEARLY" else None

        p_start, p_end = billing_date_service.compute_billing_period(
            start_date=start_date,
            interval=billing_interval,
            interval_count=interval_count,
            anchor_day=anchor_day,
            anchor_month=anchor_month,
        )

        sub_number = self._generate_subscription_number(db)
        subscription = Subscription(
            subscription_number=sub_number,
            customer_id=quote.customer_id,
            plan_id=quote.plan_id or 1,
            status="ACTIVE",
            billing_interval=billing_interval,
            interval_count=interval_count,
            billing_anchor_day=anchor_day,
            billing_anchor_month=anchor_month,
            start_date=start_date,
            current_period_start=p_start,
            current_period_end=p_end,
            next_billing_date=p_end,
            trial_end_date=None,
            currency=quote.currency,
            total_recurring_amount=quote.total_amount,
        )
        db.add(subscription)
        db.flush()

        # Copy quotation lines to subscription lines
        for q_line in quote.lines:
            sub_line = SubscriptionLine(
                subscription_id=subscription.id,
                product_id=q_line.product_id,
                variant_id=q_line.variant_id,
                quotation_line_id=q_line.id,
                description=q_line.description,
                quantity=q_line.quantity,
                unit_price=q_line.unit_price,
                discount_amount=q_line.discount_amount,
                subtotal=q_line.subtotal,
                tax_rate_id=q_line.tax_rate_id,
                tax_amount=q_line.tax_amount,
                total_amount=q_line.total_amount,
            )
            db.add(sub_line)

        # Audit lifecycle event
        event = SubscriptionEvent(
            subscription_id=subscription.id,
            event_type="CREATED",
            from_status=None,
            to_status="ACTIVE",
            description=f"Subscription created via quotation conversion ({quote.quotation_number}).",
        )
        db.add(event)

        # Update quotation status and lineage pointer
        quote.converted_subscription_id = subscription.id
        quote.status = "CONVERTED"

        db.commit()
        db.refresh(subscription)
        return subscription


quotation_service = QuotationService()
