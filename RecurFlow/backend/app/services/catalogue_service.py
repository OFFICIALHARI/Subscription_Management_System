"""Product, Variant, Plan, and Tax domain catalogue service."""

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.plan import Plan, PlanItem
from app.models.product import Product, ProductVariant
from app.models.tax import TaxRate
from app.schemas.catalogue import (
    PlanCreate,
    PlanItemCreate,
    PlanUpdate,
    ProductCreate,
    ProductUpdate,
    ProductVariantCreate,
)
from app.schemas.tax import TaxRateCreate


class CatalogueService:
    """Manages products, variants with price adjustments, billing plans, and tax rates."""

    # --- Taxes ---
    def list_tax_rates(self, db: Session, is_active: bool | None = None) -> list[TaxRate]:
        query = db.query(TaxRate)
        if is_active is not None:
            query = query.filter(TaxRate.is_active == is_active)
        return query.order_by(TaxRate.rate_percent.asc()).all()

    def create_tax_rate(self, db: Session, tax_in: TaxRateCreate) -> TaxRate:
        existing = db.query(TaxRate).filter(TaxRate.code == tax_in.code.upper()).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tax rate code '{tax_in.code}' already exists.",
            )
        tax = TaxRate(
            code=tax_in.code.upper(),
            name=tax_in.name,
            rate_percent=tax_in.rate_percent,
            is_active=tax_in.is_active,
        )
        db.add(tax)
        db.commit()
        db.refresh(tax)
        return tax

    # --- Products & Variants ---
    def list_products(self, db: Session, is_active: bool | None = None) -> list[Product]:
        query = db.query(Product).options(joinedload(Product.variants))
        if is_active is not None:
            query = query.filter(Product.is_active == is_active)
        return query.order_by(Product.name.asc()).all()

    def get_product(self, db: Session, product_id: int) -> Product:
        product = (
            db.query(Product)
            .options(joinedload(Product.variants))
            .filter(Product.id == product_id)
            .first()
        )
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with ID {product_id} not found.",
            )
        return product

    def create_product(self, db: Session, product_in: ProductCreate) -> Product:
        existing = db.query(Product).filter(Product.code == product_in.code.upper()).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Product with code '{product_in.code}' already exists.",
            )
        product = Product(
            name=product_in.name,
            code=product_in.code.upper(),
            description=product_in.description,
            base_price=product_in.base_price,
            tax_rate_id=product_in.tax_rate_id,
            is_active=product_in.is_active,
        )
        db.add(product)
        db.flush()

        for variant_in in product_in.variants:
            variant = ProductVariant(
                product_id=product.id,
                sku=variant_in.sku.upper(),
                name=variant_in.name,
                attribute_values=variant_in.attribute_values,
                price_adjustment=variant_in.price_adjustment,
                is_active=variant_in.is_active,
            )
            db.add(variant)

        db.commit()
        db.refresh(product)
        return product

    def create_variant(
        self, db: Session, product_id: int, variant_in: ProductVariantCreate
    ) -> ProductVariant:
        """Add a variant (with price adjustment e.g. +560.00) to a product."""
        product = self.get_product(db, product_id)
        existing = (
            db.query(ProductVariant).filter(ProductVariant.sku == variant_in.sku.upper()).first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Variant SKU '{variant_in.sku}' already exists.",
            )
        variant = ProductVariant(
            product_id=product.id,
            sku=variant_in.sku.upper(),
            name=variant_in.name,
            attribute_values=variant_in.attribute_values,
            price_adjustment=variant_in.price_adjustment,
            is_active=variant_in.is_active,
        )
        db.add(variant)
        db.commit()
        db.refresh(variant)
        return variant

    def update_product(
        self, db: Session, product_id: int, product_in: ProductUpdate
    ) -> Product:
        product = self.get_product(db, product_id)
        update_data = product_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        db.commit()
        db.refresh(product)
        return product

    # --- Plans ---
    def list_plans(self, db: Session, is_active: bool | None = None) -> list[Plan]:
        query = db.query(Plan).options(joinedload(Plan.items))
        if is_active is not None:
            query = query.filter(Plan.is_active == is_active)
        return query.order_by(Plan.name.asc()).all()

    def get_plan(self, db: Session, plan_id: int) -> Plan:
        plan = db.query(Plan).options(joinedload(Plan.items)).filter(Plan.id == plan_id).first()
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan with ID {plan_id} not found.",
            )
        return plan

    def create_plan(self, db: Session, plan_in: PlanCreate) -> Plan:
        existing = db.query(Plan).filter(Plan.code == plan_in.code.upper()).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Plan code '{plan_in.code}' already exists.",
            )
        plan = Plan(
            code=plan_in.code.upper(),
            name=plan_in.name,
            description=plan_in.description,
            billing_interval=plan_in.billing_interval.upper(),
            interval_count=plan_in.interval_count,
            trial_period_days=plan_in.trial_period_days,
            is_active=plan_in.is_active,
        )
        db.add(plan)
        db.flush()

        for item_in in plan_in.items:
            item = PlanItem(
                plan_id=plan.id,
                product_id=item_in.product_id,
                variant_id=item_in.variant_id,
                quantity=item_in.quantity,
                unit_price=item_in.unit_price,
                sort_order=item_in.sort_order,
            )
            db.add(item)

        db.commit()
        db.refresh(plan)
        return plan

    def update_plan(self, db: Session, plan_id: int, plan_in: PlanUpdate) -> Plan:
        plan = self.get_plan(db, plan_id)
        update_data = plan_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(plan, field, value)
        db.commit()
        db.refresh(plan)
        return plan


catalogue_service = CatalogueService()
