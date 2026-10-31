"""Ensure response schemas accept ORM-shaped objects (no drifted field names)."""

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from app.schemas.customer import CustomerResponse
from app.schemas.invoice import InvoiceLineResponse, InvoiceResponse
from app.schemas.payment import PaymentResponse
from app.schemas.quotation import QuotationResponse
from app.schemas.tax import TaxRateResponse


NOW = datetime(2026, 10, 31, tzinfo=timezone.utc)


def test_customer_schema_uses_billing_fields() -> None:
    payload = SimpleNamespace(
        id=1,
        user_id=None,
        company_name="Acme",
        contact_name="Alice",
        email="alice@acme.com",
        phone=None,
        tax_identifier=None,
        billing_address_line1="1 Main",
        billing_address_line2=None,
        billing_city="Mumbai",
        billing_state="MH",
        billing_postal_code="400001",
        billing_country="India",
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )
    model = CustomerResponse.model_validate(payload, from_attributes=True)
    assert model.billing_city == "Mumbai"


def test_tax_schema_uses_rate_percentage() -> None:
    payload = SimpleNamespace(
        id=1,
        name="GST 18%",
        rate_percentage=Decimal("18.00"),
        tax_type="EXCLUSIVE",
        description="GST",
        is_active=True,
        created_at=NOW,
        updated_at=NOW,
    )
    model = TaxRateResponse.model_validate(payload, from_attributes=True)
    assert model.rate_percentage == Decimal("18.00")


def test_quotation_schema_uses_expiration_date() -> None:
    payload = SimpleNamespace(
        id=1,
        quotation_number="QUO-2026-00001",
        customer_id=1,
        template_id=None,
        status="DRAFT",
        issue_date=date(2026, 10, 1),
        expiration_date=date(2026, 10, 31),
        currency="USD",
        subtotal=Decimal("100.00"),
        discount_amount=Decimal("0.00"),
        tax_amount=Decimal("18.00"),
        total_amount=Decimal("118.00"),
        is_converted=False,
        notes=None,
        created_at=NOW,
        updated_at=NOW,
    )
    model = QuotationResponse.model_validate(payload, from_attributes=True)
    assert model.expiration_date.day == 31


def test_invoice_line_schema_matches_orm() -> None:
    payload = SimpleNamespace(
        id=1,
        invoice_id=1,
        subscription_line_id=None,
        description_snapshot="Core",
        quantity=1,
        unit_price_snapshot=Decimal("100.00"),
        discount_amount=Decimal("0.00"),
        tax_rate_snapshot=Decimal("18.00"),
        line_subtotal=Decimal("100.00"),
        line_tax=Decimal("18.00"),
        line_total=Decimal("118.00"),
    )
    model = InvoiceLineResponse.model_validate(payload, from_attributes=True)
    assert model.line_tax == Decimal("18.00")
    invoice = InvoiceResponse.model_validate(
        SimpleNamespace(
            id=1,
            invoice_number="INV-2026-00001",
            customer_id=1,
            subscription_id=None,
            status="CONFIRMED",
            currency="USD",
            subtotal=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            tax_amount=Decimal("18.00"),
            total_amount=Decimal("118.00"),
            amount_paid=Decimal("0.00"),
            balance_due=Decimal("118.00"),
            billing_period_start=None,
            billing_period_end=None,
            issue_date=date(2026, 10, 1),
            due_date=date(2026, 10, 15),
            notes=None,
            created_at=NOW,
            updated_at=NOW,
        ),
        from_attributes=True,
    )
    assert invoice.issue_date.month == 10


def test_payment_unallocated_balance_is_computed() -> None:
    payload = SimpleNamespace(
        id=1,
        payment_number="PAY-2026-00001",
        customer_id=1,
        amount=Decimal("1000.00"),
        currency="USD",
        payment_method="BANK_TRANSFER",
        paid_at=date(2026, 10, 1),
        transaction_reference=None,
        notes=None,
        status="SUCCESS",
        amount_allocated=Decimal("400.00"),
        created_at=NOW,
        updated_at=NOW,
    )
    model = PaymentResponse.model_validate(payload, from_attributes=True)
    assert model.unallocated_balance == Decimal("600.00")
