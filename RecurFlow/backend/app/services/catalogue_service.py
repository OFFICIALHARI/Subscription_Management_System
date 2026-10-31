"""Product, Variant, Plan, and Tax domain catalogue service."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.plan import Plan, PlanItem
from app.models.product import Product, ProductVariant
from app.models.tax import TaxRate
from app.schemas.catalogue import (
    PlanCreate,
    PlanUpdate,
    ProductCreate,
    ProductUpdate,
    ProductVariantCreate,
)
from app.schemas.tax import TaxRateCreate


class CatalogueService:
    """Manages products, variants with price adjustments, billing plans, and tax rates."""

    def list_tax_rates(self, db: Session, is_active: bool | None = None) -> list[TaxRate]:
        query = db.query(TaxRate)
        if is_active is not None:
            query = query.filter(TaxRate.is_active == is_active)
        return query.order_by(TaxRate.rate_percentage.asc()).all()

    def create_tax_rate(self, db: Session, tax_in: TaxRateCreate) -> TaxRate:
        existing = db.query(TaxRate).filter(TaxRate.name == tax_in.name).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Tax rate '{tax_in.name}' already exists.",
            )
        tax = TaxRate(
            name=tax_in.name,
            rate_percentage=tax_in.rate_percentage,
            tax_type=tax_in.tax_type.upper(),
            description=tax_in.description,
            is_active=tax_in.is_active,
        )
        db.add(tax)
        db.commit()
        db.refresh(tax)
        return tax

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
        if product_in.sku:
            existing = db.query(Product).filter(Product.sku == product_in.sku.upper()).first()
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Product with SKU '{product_in.sku}' already exists.",
                )
        product = Product(
            name=product_in.name,
            product_type=product_in.product_type.upper(),
            sku=product_in.sku.upper() if product_in.sku else None,
            description=product_in.description,
            sales_price=product_in.sales_price,
            cost_price=product_in.cost_price,
            is_active=product_in.is_active,
        )
        db.add(product)
        db.flush()

        for variant_in in product_in.variants:
            variant = ProductVariant(
                product_id=product.id,
                variant_name=variant_in.variant_name,
                variant_value=variant_in.variant_value,
                sku_suffix=variant_in.sku_suffix.upper() if variant_in.sku_suffix else None,
                price_adjustment=variant_in.price_adjustment,
                is_active=variant_in.is_active,
            )
            db.add(variant)

        db.commit()
        db.refresh(product)
        return self.get_product(db, product.id)

    def create_variant(
        self, db: Session, product_id: int, variant_in: ProductVariantCreate
    ) -> ProductVariant:
        """Add a variant (with price adjustment e.g. +560.00) to a product."""
        product = self.get_product(db, product_id)
        existing = (
            db.query(ProductVariant)
            .filter(
                ProductVariant.product_id == product.id,
                ProductVariant.variant_name == variant_in.variant_name,
                ProductVariant.variant_value == variant_in.variant_value,
            )
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This product already has that variant option.",
            )
        variant = ProductVariant(
            product_id=product.id,
            variant_name=variant_in.variant_name,
            variant_value=variant_in.variant_value,
            sku_suffix=variant_in.sku_suffix.upper() if variant_in.sku_suffix else None,
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
        if "product_type" in update_data and update_data["product_type"]:
            update_data["product_type"] = update_data["product_type"].upper()
        if "sku" in update_data and update_data["sku"]:
            update_data["sku"] = update_data["sku"].upper()
        for field, value in update_data.items():
            setattr(product, field, value)
        db.commit()
        db.refresh(product)
        return product

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
            minimum_quantity=plan_in.minimum_quantity,
            is_active=plan_in.is_active,
        )
        db.add(plan)
        db.flush()

        for item_in in plan_in.items:
            item = PlanItem(
                plan_id=plan.id,
                product_id=item_in.product_id,
                product_variant_id=item_in.product_variant_id,
                quantity=item_in.quantity,
                unit_price=item_in.unit_price,
            )
            db.add(item)

        db.commit()
        return self.get_plan(db, plan.id)

    def update_plan(self, db: Session, plan_id: int, plan_in: PlanUpdate) -> Plan:
        plan = self.get_plan(db, plan_id)
        update_data = plan_in.model_dump(exclude_unset=True)
        if "billing_interval" in update_data and update_data["billing_interval"]:
            update_data["billing_interval"] = update_data["billing_interval"].upper()
        for field, value in update_data.items():
            setattr(plan, field, value)
        db.commit()
        db.refresh(plan)
        return plan


catalogue_service = CatalogueService()
