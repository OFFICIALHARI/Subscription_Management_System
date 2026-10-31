"""Discounts and promotion coupons domain service."""

from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.discount import Discount
from app.schemas.discount import DiscountCreate, DiscountUpdate, DiscountValidationResponse
from app.services.pricing_service import round_currency


class DiscountService:
    """Manages promotional discounts, coupons, and cart discount calculations."""

    def list_discounts(self, db: Session, is_active: bool | None = None) -> list[Discount]:
        query = db.query(Discount)
        if is_active is not None:
            query = query.filter(Discount.is_active == is_active)
        return query.order_by(Discount.created_at.desc()).all()

    def get_discount(self, db: Session, discount_id: int) -> Discount:
        discount = db.query(Discount).filter(Discount.id == discount_id).first()
        if not discount:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Discount with ID {discount_id} not found.",
            )
        return discount

    def get_by_code(self, db: Session, code: str) -> Discount | None:
        return db.query(Discount).filter(Discount.code == code.upper()).first()

    def create_discount(self, db: Session, discount_in: DiscountCreate) -> Discount:
        existing = self.get_by_code(db, discount_in.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Discount code '{discount_in.code}' already exists.",
            )
        discount = Discount(
            code=discount_in.code.upper(),
            name=discount_in.name,
            discount_type=discount_in.discount_type.upper(),
            discount_value=discount_in.discount_value,
            currency=discount_in.currency,
            min_order_amount=discount_in.min_order_amount,
            max_uses_total=discount_in.max_uses_total,
            starts_at=discount_in.starts_at,
            ends_at=discount_in.ends_at,
            is_active=discount_in.is_active,
        )
        db.add(discount)
        db.commit()
        db.refresh(discount)
        return discount

    def validate_code(
        self, db: Session, code: str, order_amount: Decimal
    ) -> DiscountValidationResponse:
        """Validate coupon code eligibility against order amount and date constraints."""
        discount = self.get_by_code(db, code)
        if not discount:
            return DiscountValidationResponse(
                valid=False,
                message=f"Discount code '{code}' does not exist.",
            )
        if not discount.is_active:
            return DiscountValidationResponse(
                valid=False,
                message=f"Discount code '{code}' is inactive.",
            )

        today = date.today()
        if discount.starts_at and today < discount.starts_at:
            return DiscountValidationResponse(
                valid=False,
                message=f"Discount code '{code}' is not active yet.",
            )
        if discount.ends_at and today > discount.ends_at:
            return DiscountValidationResponse(
                valid=False,
                message=f"Discount code '{code}' has expired.",
            )

        if discount.max_uses_total and discount.uses_count >= discount.max_uses_total:
            return DiscountValidationResponse(
                valid=False,
                message=f"Discount code '{code}' has reached its usage limit.",
            )

        if order_amount < discount.min_order_amount:
            return DiscountValidationResponse(
                valid=False,
                message=f"Order amount ${order_amount} is below minimum requirement of ${discount.min_order_amount}.",
            )

        # Compute calculated discount
        if discount.discount_type == "PERCENTAGE":
            calc = round_currency(order_amount * (discount.discount_value / Decimal("100.00")))
        else:
            calc = round_currency(min(discount.discount_value, order_amount))

        return DiscountValidationResponse(
            valid=True,
            message="Discount code is valid and applied.",
            discount_type=discount.discount_type,
            discount_value=discount.discount_value,
            calculated_discount_amount=calc,
        )


discount_service = DiscountService()
