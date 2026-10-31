"""Financial rounding and line-item pricing calculations."""

from decimal import Decimal, ROUND_HALF_UP

CENT = Decimal("0.01")


def round_currency(value: Decimal) -> Decimal:
    """Round monetary decimal strictly using ROUND_HALF_UP to two decimal places."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_line_totals(
    quantity: int,
    unit_price: Decimal,
    discount_amount: Decimal = Decimal("0.00"),
    tax_rate_percent: Decimal = Decimal("0.00"),
) -> dict[str, Decimal]:
    """
    Computes subtotal, discounted taxable amount, tax, and line total.
    Returns dictionary with exact Decimal values rounded to 2 decimal places.
    """
    subtotal = round_currency(Decimal(quantity) * unit_price)
    discount = round_currency(min(discount_amount, subtotal))
    taxable_base = subtotal - discount
    tax = round_currency(taxable_base * (tax_rate_percent / Decimal("100.00")))
    total = taxable_base + tax

    return {
        "subtotal": subtotal,
        "discount_amount": discount,
        "taxable_base": taxable_base,
        "tax_amount": tax,
        "total_amount": total,
    }
