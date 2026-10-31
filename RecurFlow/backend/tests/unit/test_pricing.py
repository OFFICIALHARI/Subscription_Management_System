"""Unit tests for Decimal line-item pricing."""

from decimal import Decimal

from app.services.pricing_service import calculate_line_totals, round_currency


def test_round_currency_half_up() -> None:
    assert round_currency(Decimal("1.225")) == Decimal("1.23")
    assert round_currency(Decimal("1.224")) == Decimal("1.22")


def test_line_totals_with_tax_and_discount() -> None:
    result = calculate_line_totals(
        quantity=2,
        unit_price=Decimal("100.00"),
        discount_amount=Decimal("20.00"),
        tax_rate_percent=Decimal("18.00"),
    )
    assert result["subtotal"] == Decimal("200.00")
    assert result["discount_amount"] == Decimal("20.00")
    assert result["taxable_base"] == Decimal("180.00")
    assert result["tax_amount"] == Decimal("32.40")
    assert result["total_amount"] == Decimal("212.40")
