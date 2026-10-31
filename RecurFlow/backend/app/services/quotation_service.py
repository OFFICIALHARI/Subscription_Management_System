"""Quotation domain service and atomic conversion to subscription."""

from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.plan import Plan
from app.models.product import Product, ProductVariant
from app.models.quotation import Quotation, QuotationLine
from app.models.subscription import Subscription, SubscriptionEvent, SubscriptionLine
from app.models.tax import TaxRate
from app.schemas.quotation import QuotationCreate
from app.services.billing_date_service import billing_date_service
from app.services.discount_service import discount_service
from app.services.pricing_service import calculate_line_totals, round_currency


class QuotationService:
    """Manages quotation drafts, calculations, confirmations, and conversion to subscriptions."""

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
        issue_date = quote_in.issue_date or date.today()
        if quote_in.expiration_date < issue_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Expiration date must be on or after the issue date.",
            )

        lines_to_add: list[dict] = []
        raw_lines = quote_in.lines

        if not raw_lines and quote_in.plan_id:
            plan = (
                db.query(Plan)
                .options(joinedload(Plan.items))
                .filter(Plan.id == quote_in.plan_id)
                .first()
            )
            if not plan:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Plan with ID {quote_in.plan_id} not found.",
                )
            if not plan.items:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="The selected plan has no items to quote.",
                )
            for item in plan.items:
                prod = db.query(Product).filter(Product.id == item.product_id).first()
                lines_to_add.append(
                    {
                        "product_id": item.product_id,
                        "product_variant_id": item.product_variant_id,
                        "plan_id": plan.id,
                        "description": prod.name if prod else "Subscription line item",
                        "quantity": item.quantity,
                        "unit_price": item.unit_price,
                        "discount_rate": Decimal("0.00"),
                        "tax_rate_id": quote_in.tax_rate_id,
                    }
                )

        for line_in in raw_lines:
            prod = db.query(Product).filter(Product.id == line_in.product_id).first()
            if not prod:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {line_in.product_id} not found.",
                )
            desc = line_in.description or prod.name
            if line_in.product_variant_id:
                variant = (
                    db.query(ProductVariant)
                    .filter(ProductVariant.id == line_in.product_variant_id)
                    .first()
                )
                if variant:
                    desc = f"{desc} — {variant.variant_name}: {variant.variant_value}"
            lines_to_add.append(
                {
                    "product_id": line_in.product_id,
                    "product_variant_id": line_in.product_variant_id,
                    "plan_id": line_in.plan_id or quote_in.plan_id,
                    "description": desc,
                    "quantity": line_in.quantity,
                    "unit_price": line_in.unit_price,
                    "discount_rate": line_in.discount_rate,
                    "tax_rate_id": line_in.tax_rate_id or quote_in.tax_rate_id,
                }
            )

        if not lines_to_add:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A quotation requires at least one line item or a plan with items.",
            )

        quotation = Quotation(
            quotation_number=self._generate_quotation_number(db),
            customer_id=quote_in.customer_id,
            template_id=quote_in.template_id,
            status="DRAFT",
            issue_date=issue_date,
            expiration_date=quote_in.expiration_date,
            currency=quote_in.currency.upper(),
            notes=quote_in.notes,
            is_converted=False,
        )
        db.add(quotation)
        db.flush()

        total_subtotal = Decimal("0.00")
        total_tax = Decimal("0.00")
        total_line_discount = Decimal("0.00")

        for line_data in lines_to_add:
            tax_rate_percent = Decimal("0.00")
            if line_data["tax_rate_id"]:
                tax_obj = db.query(TaxRate).filter(TaxRate.id == line_data["tax_rate_id"]).first()
                if tax_obj:
                    tax_rate_percent = tax_obj.rate_percentage

            raw_subtotal = round_currency(
                Decimal(line_data["quantity"]) * Decimal(str(line_data["unit_price"]))
            )
            line_discount = round_currency(
                raw_subtotal * (Decimal(str(line_data["discount_rate"])) / Decimal("100.00"))
            )
            computed = calculate_line_totals(
                quantity=line_data["quantity"],
                unit_price=line_data["unit_price"],
                discount_amount=line_discount,
                tax_rate_percent=tax_rate_percent,
            )

            q_line = QuotationLine(
                quotation_id=quotation.id,
                product_id=line_data["product_id"],
                product_variant_id=line_data["product_variant_id"],
                plan_id=line_data["plan_id"],
                description_snapshot=line_data["description"],
                quantity=line_data["quantity"],
                unit_price_snapshot=line_data["unit_price"],
                discount_rate=line_data["discount_rate"],
                tax_rate_id=line_data["tax_rate_id"],
                tax_rate_snapshot=tax_rate_percent,
                line_subtotal=computed["subtotal"],
                line_tax=computed["tax_amount"],
                line_total=computed["total_amount"],
            )
            db.add(q_line)
            total_subtotal += computed["subtotal"]
            total_tax += computed["tax_amount"]
            total_line_discount += computed["discount_amount"]

        quote_discount_amount = total_line_discount
        if quote_in.discount_code:
            v_res = discount_service.validate_code(db, quote_in.discount_code, total_subtotal)
            if not v_res.valid:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=v_res.message,
                )
            quote_discount_amount = round_currency(
                quote_discount_amount + v_res.calculated_discount_amount
            )

        quotation.subtotal = total_subtotal
        quotation.discount_amount = quote_discount_amount
        quotation.tax_amount = total_tax
        quotation.total_amount = round_currency(total_subtotal - quote_discount_amount + total_tax)
        if quotation.total_amount < Decimal("0.00"):
            quotation.total_amount = Decimal("0.00")

        db.commit()
        return self.get_quotation(db, quotation.id)

    def confirm_quotation(self, db: Session, quotation_id: int) -> Quotation:
        """Mark quotation as CONFIRMED."""
        quote = self.get_quotation(db, quotation_id)
        if quote.is_converted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot confirm a quotation that has already been converted.",
            )
        if quote.status in ["CANCELLED", "EXPIRED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot confirm quotation in state '{quote.status}'.",
            )
        quote.status = "CONFIRMED"
        db.commit()
        db.refresh(quote)
        return quote

    def convert_to_subscription(self, db: Session, quotation_id: int) -> Subscription:
        """Atomically convert a confirmed quotation into an active subscription."""
        quote = self.get_quotation(db, quotation_id)
        if quote.is_converted:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Quotation {quote.quotation_number} has already been converted.",
            )
        if quote.status in ["CANCELLED", "EXPIRED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot convert quotation in state '{quote.status}'.",
            )
        if quote.status != "CONFIRMED":
            quote.status = "CONFIRMED"

        if not quote.lines:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot convert a quotation with zero line items to a subscription.",
            )

        plan_id = next((line.plan_id for line in quote.lines if line.plan_id), None)
        if not plan_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quotation must reference a subscription plan on at least one line.",
            )
        plan = db.query(Plan).filter(Plan.id == plan_id).first()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The plan referenced by this quotation no longer exists.",
            )

        billing_interval = plan.billing_interval
        interval_count = plan.interval_count
        start_date = date.today()
        anchor_day = start_date.day
        _p_start, p_end = billing_date_service.compute_billing_period(
            period_start=start_date,
            interval=billing_interval,  # type: ignore[arg-type]
            interval_count=interval_count,
            anchor_day=anchor_day,
        )

        recurring = round_currency(
            sum((line.line_subtotal for line in quote.lines), Decimal("0.00"))
        )

        subscription = Subscription(
            subscription_number=self._generate_subscription_number(db),
            customer_id=quote.customer_id,
            plan_id=plan.id,
            originating_quotation_id=quote.id,
            status="ACTIVE",
            start_date=start_date,
            end_date=None,
            billing_anchor_day=anchor_day,
            next_billing_date=p_end,
            payment_terms_days=15,
            currency=quote.currency,
            recurring_amount=recurring,
        )
        db.add(subscription)
        db.flush()

        for q_line in quote.lines:
            sub_line = SubscriptionLine(
                subscription_id=subscription.id,
                product_id=q_line.product_id,
                product_variant_id=q_line.product_variant_id,
                quotation_line_id=q_line.id,
                description_snapshot=q_line.description_snapshot,
                quantity=q_line.quantity,
                unit_price_snapshot=q_line.unit_price_snapshot,
                tax_rate_id=q_line.tax_rate_id,
                tax_rate_snapshot=q_line.tax_rate_snapshot,
            )
            db.add(sub_line)

        event = SubscriptionEvent(
            subscription_id=subscription.id,
            event_type="CREATED",
            from_status=None,
            to_status="ACTIVE",
            reason=f"Subscription created from quotation {quote.quotation_number}.",
        )
        db.add(event)

        quote.is_converted = True
        quote.status = "CONFIRMED"

        db.commit()
        db.refresh(subscription)
        return subscription


quotation_service = QuotationService()
