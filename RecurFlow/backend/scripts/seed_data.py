"""Idempotent seed script for RecurFlow demonstration and test data."""

import logging
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.customer import Customer
from app.models.discount import Discount
from app.models.invoice import Invoice, InvoiceLine
from app.models.payment import Payment, PaymentAllocation
from app.models.plan import Plan, PlanItem
from app.models.product import Product, ProductVariant
from app.models.quotation import Quotation, QuotationLine, QuotationTemplate
from app.models.subscription import Subscription, SubscriptionEvent, SubscriptionLine
from app.models.tax import TaxRate
from app.models.user import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("recurflow.seed")


def seed_all(db: Session) -> None:
    logger.info("Beginning idempotent seed execution...")

    # 1. Users & Passwords
    # Password policy: >8 chars, uppercase, lowercase, special/digit
    users_data = [
        {"email": "admin@recurflow.com", "role": "ADMIN", "pw": "AdminPassword123!"},
        {"email": "staff@recurflow.com", "role": "STAFF", "pw": "StaffPassword123!"},
        {"email": "portal@acme.com", "role": "CUSTOMER", "pw": "CustomerPassword123!"},
        {"email": "portal@brightloop.com", "role": "CUSTOMER", "pw": "CustomerPassword123!"},
    ]

    users_map: dict[str, User] = {}
    for u in users_data:
        existing = db.scalars(select(User).where(User.email == u["email"])).first()
        if not existing:
            user = User(
                email=u["email"],
                hashed_password=hash_password(u["pw"]),
                role=u["role"],
                is_active=True,
            )
            db.add(user)
            db.flush()
            users_map[u["email"]] = user
            logger.info("Created user: %s (%s)", u["email"], u["role"])
        else:
            users_map[u["email"]] = existing

    # 2. Customers
    cust_data = [
        {
            "company_name": "Acme Technologies Inc",
            "contact_name": "Alice Johnson",
            "email": "alice@acme.com",
            "phone": "+1-555-0199",
            "tax_id": "US-EIN-9928172",
            "address": "100 Market Street",
            "city": "San Francisco",
            "state": "California",
            "zip": "94105",
            "country": "United States",
            "user_email": "portal@acme.com",
        },
        {
            "company_name": "Brightloop Digital Systems",
            "contact_name": "Brian Davies",
            "email": "brian@brightloop.com",
            "phone": "+91-9876543210",
            "tax_id": "27AABCB1234D1Z2",
            "address": "Level 4, Cyber City",
            "city": "Mumbai",
            "state": "Maharashtra",
            "zip": "400051",
            "country": "India",
            "user_email": "portal@brightloop.com",
        },
        {
            "company_name": "Vertex Global Analytics",
            "contact_name": "Victoria Vance",
            "email": "vance@vertex.io",
            "phone": "+44-20-7946-0912",
            "tax_id": "GB-VAT-123456789",
            "address": "88 King William St",
            "city": "London",
            "state": "Greater London",
            "zip": "EC4N 7DA",
            "country": "United Kingdom",
            "user_email": None,
        },
    ]

    customers_map: dict[str, Customer] = {}
    for c in cust_data:
        existing_c = db.scalars(select(Customer).where(Customer.company_name == c["company_name"])).first()
        if not existing_c:
            cust = Customer(
                user_id=users_map[c["user_email"]].id if c["user_email"] else None,
                company_name=c["company_name"],
                contact_name=c["contact_name"],
                email=c["email"],
                phone=c["phone"],
                tax_identifier=c["tax_id"],
                billing_address_line1=c["address"],
                billing_city=c["city"],
                billing_state=c["state"],
                billing_postal_code=c["zip"],
                billing_country=c["country"],
                is_active=True,
            )
            db.add(cust)
            db.flush()
            customers_map[c["company_name"]] = cust
            logger.info("Created customer: %s", c["company_name"])
        else:
            customers_map[c["company_name"]] = existing_c

    # 3. Tax Rates
    taxes_data = [
        {"name": "GST 18%", "rate": Decimal("18.00"), "type": "EXCLUSIVE", "desc": "Standard Indian GST"},
        {"name": "VAT 20%", "rate": Decimal("20.00"), "type": "EXCLUSIVE", "desc": "UK / European VAT"},
        {"name": "Zero Rated Tax 0%", "rate": Decimal("0.00"), "type": "EXCLUSIVE", "desc": "Tax Exempt"},
    ]
    taxes_map: dict[str, TaxRate] = {}
    for t in taxes_data:
        existing_t = db.scalars(select(TaxRate).where(TaxRate.name == t["name"])).first()
        if not existing_t:
            tr = TaxRate(
                name=t["name"],
                rate_percentage=t["rate"],
                tax_type=t["type"],
                description=t["desc"],
                is_active=True,
            )
            db.add(tr)
            db.flush()
            taxes_map[t["name"]] = tr
            logger.info("Created tax rate: %s (%s%%)", t["name"], t["rate"])
        else:
            taxes_map[t["name"]] = existing_t

    # 4. Products & Variants (with required +560.00 variant price adjustment example)
    prod_data = [
        {
            "name": "RecurFlow SaaS Core Platform",
            "type": "SOFTWARE",
            "sku": "RF-SAAS-CORE",
            "sales_price": Decimal("1000.00"),
            "cost_price": Decimal("200.00"),
            "desc": "Core multi-tenant subscription operations engine",
            "variants": [
                {
                    "name": "Edition",
                    "value": "Enterprise Tier",
                    "sku_suffix": "ENT",
                    "adj": Decimal("560.00"),  # REQUIRED ODOO BRAND EXAMPLE: +560.00
                },
                {
                    "name": "Edition",
                    "value": "Professional Tier",
                    "sku_suffix": "PRO",
                    "adj": Decimal("250.00"),
                },
            ],
        },
        {
            "name": "High-Bandwidth Cloud Storage",
            "type": "SERVICE",
            "sku": "RF-STOR-1TB",
            "sales_price": Decimal("200.00"),
            "cost_price": Decimal("50.00"),
            "desc": "1TB secure managed S3 storage block",
            "variants": [
                {"name": "Redundancy", "value": "Multi-Region Geo", "sku_suffix": "GEO", "adj": Decimal("100.00")}
            ],
        },
        {
            "name": "24/7 Dedicated Technical Support SLA",
            "type": "SERVICE",
            "sku": "RF-SLA-247",
            "sales_price": Decimal("500.00"),
            "cost_price": Decimal("150.00"),
            "desc": "1-hour guaranteed incident response SLA",
            "variants": [],
        },
    ]

    products_map: dict[str, Product] = {}
    variants_map: dict[str, ProductVariant] = {}
    for p in prod_data:
        existing_p = db.scalars(select(Product).where(Product.sku == p["sku"])).first()
        if not existing_p:
            prod = Product(
                name=p["name"],
                product_type=p["type"],
                sku=p["sku"],
                sales_price=p["sales_price"],
                cost_price=p["cost_price"],
                description=p["desc"],
                is_active=True,
            )
            db.add(prod)
            db.flush()
            products_map[p["name"]] = prod

            for v in p["variants"]:
                var = ProductVariant(
                    product_id=prod.id,
                    variant_name=v["name"],
                    variant_value=v["value"],
                    sku_suffix=v["sku_suffix"],
                    price_adjustment=v["adj"],
                    is_active=True,
                )
                db.add(var)
                db.flush()
                variants_map[f"{p['name']}:{v['value']}"] = var
                logger.info("Created variant for %s: %s (+%s)", p["name"], v["value"], v["adj"])
        else:
            products_map[p["name"]] = existing_p

    # 5. Plans (Daily, Weekly, Monthly, Yearly)
    plans_data = [
        {"name": "RecurFlow Daily Trial", "code": "RF-DAILY", "interval": "DAILY", "count": 1, "price": Decimal("50.00")},
        {"name": "RecurFlow Weekly Sprint", "code": "RF-WEEKLY", "interval": "WEEKLY", "count": 1, "price": Decimal("300.00")},
        {"name": "RecurFlow Business Monthly", "code": "RF-MONTHLY", "interval": "MONTHLY", "count": 1, "price": Decimal("1200.00")},
        {"name": "RecurFlow Enterprise Annual", "code": "RF-YEARLY", "interval": "YEARLY", "count": 1, "price": Decimal("12000.00")},
    ]

    plans_map: dict[str, Plan] = {}
    for pl in plans_data:
        existing_pl = db.scalars(select(Plan).where(Plan.code == pl["code"])).first()
        if not existing_pl:
            plan = Plan(
                name=pl["name"],
                code=pl["code"],
                description=f"Standard {pl['interval']} commitment plan",
                billing_interval=pl["interval"],
                interval_count=pl["count"],
                trial_period_days=0,
                minimum_quantity=1,
                is_active=True,
            )
            db.add(plan)
            db.flush()
            plans_map[pl["code"]] = plan

            # Link base product item
            core_prod = products_map["RecurFlow SaaS Core Platform"]
            plan_item = PlanItem(
                plan_id=plan.id,
                product_id=core_prod.id,
                quantity=1,
                unit_price=pl["price"],
            )
            db.add(plan_item)
            logger.info("Created plan: %s (%s)", pl["name"], pl["interval"])
        else:
            plans_map[pl["code"]] = existing_pl

    # 6. Discounts
    disc_data = [
        {
            "code": "FOUNDER50",
            "name": "Founding Customer Discount",
            "type": "PERCENTAGE",
            "value": Decimal("20.00"),  # 20%
            "min_order": Decimal("500.00"),
            "max_uses": 50,
            "max_per_cust": 1,
        },
        {
            "code": "WELCOME100",
            "name": "Onboarding Fixed Credit",
            "type": "FIXED_AMOUNT",
            "value": Decimal("100.00"),  # $100
            "min_order": Decimal("300.00"),
            "max_uses": 100,
            "max_per_cust": 1,
        },
    ]
    discounts_map: dict[str, Discount] = {}
    today = date.today()
    for d in disc_data:
        existing_d = db.scalars(select(Discount).where(Discount.code == d["code"])).first()
        if not existing_d:
            disc = Discount(
                code=d["code"],
                name=d["name"],
                discount_type=d["type"],
                discount_value=d["value"],
                min_order_amount=d["min_order"],
                max_uses_total=d["max_uses"],
                uses_count=0,
                max_uses_per_customer=d["max_per_cust"],
                start_date=today - timedelta(days=30),
                end_date=today + timedelta(days=365),
                is_active=True,
            )
            db.add(disc)
            db.flush()
            discounts_map[d["code"]] = disc
            logger.info("Created discount: %s (%s)", d["code"], d["name"])
        else:
            discounts_map[d["code"]] = existing_d

    # 7. Quotation Template & Quotations
    existing_tmpl = db.scalars(select(QuotationTemplate).where(QuotationTemplate.name == "Standard SaaS Onboarding")).first()
    if not existing_tmpl:
        tmpl = QuotationTemplate(
            name="Standard SaaS Onboarding",
            description="Default proposal package for new enterprise accounts",
            default_validity_days=30,
            is_active=True,
        )
        db.add(tmpl)
        db.flush()
        logger.info("Created quotation template: Standard SaaS Onboarding")
    else:
        tmpl = existing_tmpl

    # Quotation 1: Confirmed and converted to subscription
    acme_cust = customers_map["Acme Technologies Inc"]
    core_prod = products_map["RecurFlow SaaS Core Platform"]
    ent_variant = variants_map.get("RecurFlow SaaS Core Platform:Enterprise Tier")
    tax_18 = taxes_map["GST 18%"]

    existing_q1 = db.scalars(select(Quotation).where(Quotation.quotation_number == "QUO-2026-00001")).first()
    if not existing_q1:
        # Base 1000 + Variant 560 = 1560.00
        unit_p = Decimal("1560.00")
        subtotal = unit_p
        tax_amt = Decimal("280.80")  # 18% of 1560
        total_amt = subtotal + tax_amt

        q1 = Quotation(
            quotation_number="QUO-2026-00001",
            customer_id=acme_cust.id,
            template_id=tmpl.id,
            status="CONFIRMED",
            issue_date=today - timedelta(days=45),
            expiration_date=today + timedelta(days=15),
            currency="USD",
            subtotal=subtotal,
            discount_amount=Decimal("0.00"),
            tax_amount=tax_amt,
            total_amount=total_amt,
            is_converted=True,
            notes="Enterprise package with +560 tier adjustment",
        )
        db.add(q1)
        db.flush()

        ql1 = QuotationLine(
            quotation_id=q1.id,
            product_id=core_prod.id,
            product_variant_id=ent_variant.id if ent_variant else None,
            plan_id=plans_map["RF-MONTHLY"].id,
            description_snapshot="RecurFlow SaaS Core Platform - Enterprise Tier (+560.00)",
            quantity=1,
            unit_price_snapshot=unit_p,
            discount_rate=Decimal("0.00"),
            tax_rate_id=tax_18.id,
            tax_rate_snapshot=tax_18.rate_percentage,
            line_subtotal=subtotal,
            line_tax=tax_amt,
            line_total=total_amt,
        )
        db.add(ql1)
        db.flush()
        logger.info("Created quotation: QUO-2026-00001 (Converted)")
    else:
        q1 = existing_q1

    # 8. Subscriptions (Active, Paused, Closed)
    # Active Subscription (Acme)
    existing_sub1 = db.scalars(select(Subscription).where(Subscription.subscription_number == "SUB-2026-00001")).first()
    if not existing_sub1:
        sub1 = Subscription(
            subscription_number="SUB-2026-00001",
            customer_id=acme_cust.id,
            plan_id=plans_map["RF-MONTHLY"].id,
            originating_quotation_id=q1.id,
            status="ACTIVE",
            start_date=today - timedelta(days=45),
            end_date=None,  # Perpetual
            billing_anchor_day=15,
            next_billing_date=today + timedelta(days=15),
            payment_terms_days=15,
            currency="USD",
            recurring_amount=Decimal("1560.00"),
        )
        db.add(sub1)
        db.flush()

        sub1_line = SubscriptionLine(
            subscription_id=sub1.id,
            product_id=core_prod.id,
            product_variant_id=ent_variant.id if ent_variant else None,
            description_snapshot="RecurFlow SaaS Core Platform - Enterprise Tier (+560.00)",
            quantity=1,
            unit_price_snapshot=Decimal("1560.00"),
            tax_rate_id=tax_18.id,
            tax_rate_snapshot=tax_18.rate_percentage,
        )
        db.add(sub1_line)

        db.add(SubscriptionEvent(
            subscription_id=sub1.id,
            event_type="ACTIVATED",
            to_status="ACTIVE",
            reason="Converted from Quotation QUO-2026-00001",
        ))
        logger.info("Created subscription: SUB-2026-00001 (ACTIVE)")
    else:
        sub1 = existing_sub1

    # Paused Subscription (Brightloop)
    bright_cust = customers_map["Brightloop Digital Systems"]
    existing_sub2 = db.scalars(select(Subscription).where(Subscription.subscription_number == "SUB-2026-00002")).first()
    if not existing_sub2:
        sub2 = Subscription(
            subscription_number="SUB-2026-00002",
            customer_id=bright_cust.id,
            plan_id=plans_map["RF-MONTHLY"].id,
            status="PAUSED",
            start_date=today - timedelta(days=60),
            end_date=None,
            billing_anchor_day=31,  # Month-end anchor
            next_billing_date=today + timedelta(days=20),
            payment_terms_days=15,
            currency="USD",
            recurring_amount=Decimal("1200.00"),
            paused_at=today - timedelta(days=10),
            auto_close_reason=None,
        )
        db.add(sub2)
        db.flush()

        db.add(SubscriptionEvent(
            subscription_id=sub2.id,
            event_type="PAUSED",
            from_status="ACTIVE",
            to_status="PAUSED",
            reason="Customer requested seasonal maintenance suspension",
        ))
        logger.info("Created subscription: SUB-2026-00002 (PAUSED, Anchor=31)")

    # 9. Invoices & Payments (Paid, Partially Paid, Overdue, Outstanding)
    # Invoice 1: Fully Paid (Acme)
    existing_inv1 = db.scalars(select(Invoice).where(Invoice.invoice_number == "INV-2026-00001")).first()
    if not existing_inv1:
        inv1_subtotal = Decimal("1560.00")
        inv1_tax = Decimal("280.80")
        inv1_total = inv1_subtotal + inv1_tax

        inv1 = Invoice(
            invoice_number="INV-2026-00001",
            customer_id=acme_cust.id,
            subscription_id=sub1.id,
            billing_period_start=today - timedelta(days=45),
            billing_period_end=today - timedelta(days=15),
            issue_date=today - timedelta(days=45),
            due_date=today - timedelta(days=30),
            status="PAID",
            currency="USD",
            subtotal=inv1_subtotal,
            discount_amount=Decimal("0.00"),
            tax_amount=inv1_tax,
            total_amount=inv1_total,
            amount_paid=inv1_total,
            balance_due=Decimal("0.00"),
            notes="Initial period recurring invoice - Settled in full",
        )
        db.add(inv1)
        db.flush()

        inv1_line = InvoiceLine(
            invoice_id=inv1.id,
            description_snapshot="RecurFlow SaaS Core Platform - Enterprise Tier (+560.00)",
            quantity=1,
            unit_price_snapshot=Decimal("1560.00"),
            tax_rate_snapshot=Decimal("18.00"),
            line_subtotal=inv1_subtotal,
            line_tax=inv1_tax,
            line_total=inv1_total,
        )
        db.add(inv1_line)

        # Payment for Invoice 1
        pay1 = Payment(
            payment_number="PAY-2026-00001",
            customer_id=acme_cust.id,
            payment_method="BANK_TRANSFER",
            amount=inv1_total,
            amount_allocated=inv1_total,
            currency="USD",
            paid_at=today - timedelta(days=40),
            transaction_reference="WIRE-REF-994821",
            status="SUCCESS",
            notes="Full settlement wire transfer",
        )
        db.add(pay1)
        db.flush()

        # Allocation
        alloc1 = PaymentAllocation(
            payment_id=pay1.id,
            invoice_id=inv1.id,
            allocated_amount=inv1_total,
        )
        db.add(alloc1)
        logger.info("Created invoice INV-2026-00001 (PAID) and payment PAY-2026-00001")

    # Invoice 2: Partially Paid (Brightloop)
    existing_inv2 = db.scalars(select(Invoice).where(Invoice.invoice_number == "INV-2026-00002")).first()
    if not existing_inv2:
        inv2_subtotal = Decimal("1200.00")
        inv2_tax = Decimal("216.00")
        inv2_total = Decimal("1416.00")
        paid_portion = Decimal("600.00")
        balance_due = inv2_total - paid_portion

        inv2 = Invoice(
            invoice_number="INV-2026-00002",
            customer_id=bright_cust.id,
            billing_period_start=today - timedelta(days=30),
            billing_period_end=today,
            issue_date=today - timedelta(days=30),
            due_date=today + timedelta(days=15),
            status="PARTIALLY_PAID",
            currency="USD",
            subtotal=inv2_subtotal,
            discount_amount=Decimal("0.00"),
            tax_amount=inv2_tax,
            total_amount=inv2_total,
            amount_paid=paid_portion,
            balance_due=balance_due,
            notes="Milestone payment applied",
        )
        db.add(inv2)
        db.flush()

        db.add(InvoiceLine(
            invoice_id=inv2.id,
            description_snapshot="RecurFlow Business Monthly Subscription",
            quantity=1,
            unit_price_snapshot=Decimal("1200.00"),
            tax_rate_snapshot=Decimal("18.00"),
            line_subtotal=inv2_subtotal,
            line_tax=inv2_tax,
            line_total=inv2_total,
        ))

        pay2 = Payment(
            payment_number="PAY-2026-00002",
            customer_id=bright_cust.id,
            payment_method="CHEQUE",
            amount=Decimal("1000.00"),
            amount_allocated=paid_portion,  # 600 allocated, 400 unallocated balance
            currency="USD",
            paid_at=today - timedelta(days=20),
            transaction_reference="CHQ-778811",
            status="SUCCESS",
            notes="Cheque deposit - partial allocation",
        )
        db.add(pay2)
        db.flush()

        db.add(PaymentAllocation(
            payment_id=pay2.id,
            invoice_id=inv2.id,
            allocated_amount=paid_portion,
        ))
        logger.info("Created invoice INV-2026-00002 (PARTIALLY_PAID) and payment PAY-2026-00002 (400.00 unallocated)")

    # Invoice 3: Overdue (Vertex)
    vertex_cust = customers_map["Vertex Global Analytics"]
    existing_inv3 = db.scalars(select(Invoice).where(Invoice.invoice_number == "INV-2026-00003")).first()
    if not existing_inv3:
        inv3_total = Decimal("1440.00")
        inv3 = Invoice(
            invoice_number="INV-2026-00003",
            customer_id=vertex_cust.id,
            issue_date=today - timedelta(days=45),
            due_date=today - timedelta(days=15),  # Passed 15 days ago -> OVERDUE
            status="OVERDUE",
            currency="USD",
            subtotal=Decimal("1200.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("240.00"),
            total_amount=inv3_total,
            amount_paid=Decimal("0.00"),
            balance_due=inv3_total,
            notes="Payment reminder issued",
        )
        db.add(inv3)
        db.flush()

        db.add(InvoiceLine(
            invoice_id=inv3.id,
            description_snapshot="RecurFlow Business Monthly Service + Cloud Analytics",
            quantity=1,
            unit_price_snapshot=Decimal("1200.00"),
            tax_rate_snapshot=Decimal("20.00"),
            line_subtotal=Decimal("1200.00"),
            line_tax=Decimal("240.00"),
            line_total=inv3_total,
        ))
        logger.info("Created invoice INV-2026-00003 (OVERDUE)")

    db.commit()
    logger.info("Seed execution successfully completed! All demo records committed.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_all(db)
    finally:
        db.close()
