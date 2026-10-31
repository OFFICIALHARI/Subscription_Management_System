"""Unit tests for payment allocation financial invariants, balance tracking, and over-allocation prevention."""

from decimal import Decimal

import pytest

from app.services.payment_allocation_service import (
    AllocationError,
    CustomerMismatchError,
    InvalidInvoiceStateError,
    InvoiceOverPaymentError,
    OverAllocationError,
    payment_allocation_service,
)


def test_successful_full_payment_allocation() -> None:
    """Scenario 1: Full settlement of an invoice by a single payment."""
    # Payment = 1000.00, Invoice = 1000.00, Allocation = 1000.00
    payment_allocation_service.validate_allocation_eligibility(
        payment_amount=Decimal("1000.00"),
        payment_allocated=Decimal("0.00"),
        payment_status="SUCCESS",
        invoice_total=Decimal("1000.00"),
        invoice_paid=Decimal("0.00"),
        invoice_status="CONFIRMED",
        allocation_amount=Decimal("1000.00"),
        payment_customer_id=1,
        invoice_customer_id=1,
    )

    new_paid, balance_due, new_allocated = payment_allocation_service.calculate_new_balances(
        current_invoice_total=Decimal("1000.00"),
        current_invoice_paid=Decimal("0.00"),
        current_payment_allocated=Decimal("0.00"),
        allocation_amount=Decimal("1000.00"),
    )

    assert new_paid == Decimal("1000.00")
    assert balance_due == Decimal("0.00")
    assert new_allocated == Decimal("1000.00")

    status = payment_allocation_service.derive_invoice_status(
        total_amount=Decimal("1000.00"), amount_paid=new_paid
    )
    assert status == "PAID"


def test_partial_payment_allocation() -> None:
    """Scenario 2: Partial payment of 400.00 against 1000.00 invoice."""
    new_paid, balance_due, new_allocated = payment_allocation_service.calculate_new_balances(
        current_invoice_total=Decimal("1000.00"),
        current_invoice_paid=Decimal("0.00"),
        current_payment_allocated=Decimal("0.00"),
        allocation_amount=Decimal("400.00"),
    )

    assert new_paid == Decimal("400.00")
    assert balance_due == Decimal("600.00")
    assert new_allocated == Decimal("400.00")

    status = payment_allocation_service.derive_invoice_status(
        total_amount=Decimal("1000.00"), amount_paid=new_paid
    )
    assert status == "PARTIALLY_PAID"


def test_one_payment_allocated_across_multiple_invoices() -> None:
    """Scenario 3: Single payment of 1500.00 allocated to Invoice A (1000) and Invoice B (500)."""
    payment_amount = Decimal("1500.00")
    payment_allocated = Decimal("0.00")

    # Allocation 1 to Invoice A (1000.00)
    payment_allocation_service.validate_allocation_eligibility(
        payment_amount=payment_amount,
        payment_allocated=payment_allocated,
        payment_status="SUCCESS",
        invoice_total=Decimal("1000.00"),
        invoice_paid=Decimal("0.00"),
        invoice_status="CONFIRMED",
        allocation_amount=Decimal("1000.00"),
        payment_customer_id=10,
        invoice_customer_id=10,
    )
    payment_allocated += Decimal("1000.00")

    # Allocation 2 to Invoice B (500.00)
    payment_allocation_service.validate_allocation_eligibility(
        payment_amount=payment_amount,
        payment_allocated=payment_allocated,
        payment_status="SUCCESS",
        invoice_total=Decimal("500.00"),
        invoice_paid=Decimal("0.00"),
        invoice_status="CONFIRMED",
        allocation_amount=Decimal("500.00"),
        payment_customer_id=10,
        invoice_customer_id=10,
    )
    payment_allocated += Decimal("500.00")

    assert payment_allocated == payment_amount  # Fully consumed


def test_multiple_payments_applied_to_one_invoice() -> None:
    """Scenario 4: Two separate payments (400.00 + 600.00) settle a 1000.00 invoice."""
    invoice_total = Decimal("1000.00")
    invoice_paid = Decimal("0.00")

    # First payment allocation of 400
    new_paid_1, balance_1, _ = payment_allocation_service.calculate_new_balances(
        current_invoice_total=invoice_total,
        current_invoice_paid=invoice_paid,
        current_payment_allocated=Decimal("0.00"),
        allocation_amount=Decimal("400.00"),
    )
    assert new_paid_1 == Decimal("400.00")
    assert balance_1 == Decimal("600.00")

    # Second payment allocation of 600
    new_paid_2, balance_2, _ = payment_allocation_service.calculate_new_balances(
        current_invoice_total=invoice_total,
        current_invoice_paid=new_paid_1,
        current_payment_allocated=Decimal("0.00"),
        allocation_amount=Decimal("600.00"),
    )
    assert new_paid_2 == Decimal("1000.00")
    assert balance_2 == Decimal("0.00")
    assert payment_allocation_service.derive_invoice_status(invoice_total, new_paid_2) == "PAID"


def test_attempted_allocation_beyond_payment_amount() -> None:
    """Scenario 5: Attempt to allocate 600 from a 500 payment raises OverAllocationError."""
    with pytest.raises(OverAllocationError) as exc_info:
        payment_allocation_service.validate_allocation_eligibility(
            payment_amount=Decimal("500.00"),
            payment_allocated=Decimal("0.00"),
            payment_status="SUCCESS",
            invoice_total=Decimal("1000.00"),
            invoice_paid=Decimal("0.00"),
            invoice_status="CONFIRMED",
            allocation_amount=Decimal("600.00"),
            payment_customer_id=1,
            invoice_customer_id=1,
        )
    assert "only 500.00 unallocated balance remains" in str(exc_info.value)


def test_attempted_allocation_beyond_invoice_balance() -> None:
    """Scenario 6: Attempt to allocate 400 to an invoice with only 200 balance due."""
    with pytest.raises(InvoiceOverPaymentError) as exc_info:
        payment_allocation_service.validate_allocation_eligibility(
            payment_amount=Decimal("1000.00"),
            payment_allocated=Decimal("0.00"),
            payment_status="SUCCESS",
            invoice_total=Decimal("500.00"),
            invoice_paid=Decimal("300.00"),  # balance is 200
            invoice_status="PARTIALLY_PAID",
            allocation_amount=Decimal("400.00"),
            payment_customer_id=1,
            invoice_customer_id=1,
        )
    assert "balance due is only 200.00" in str(exc_info.value)


def test_inconsistent_customer_allocation_rejected() -> None:
    """Scenario 7: Allocation across different customers is rejected."""
    with pytest.raises(CustomerMismatchError):
        payment_allocation_service.validate_allocation_eligibility(
            payment_amount=Decimal("1000.00"),
            payment_allocated=Decimal("0.00"),
            payment_status="SUCCESS",
            invoice_total=Decimal("500.00"),
            invoice_paid=Decimal("0.00"),
            invoice_status="CONFIRMED",
            allocation_amount=Decimal("500.00"),
            payment_customer_id=1,
            invoice_customer_id=2,  # Different customer!
        )


def test_failed_payment_cannot_be_allocated() -> None:
    """Scenario 8 & 9: FAILED or CANCELLED payments cannot be allocated."""
    with pytest.raises(AllocationError) as exc:
        payment_allocation_service.validate_allocation_eligibility(
            payment_amount=Decimal("1000.00"),
            payment_allocated=Decimal("0.00"),
            payment_status="CANCELLED",
            invoice_total=Decimal("500.00"),
            invoice_paid=Decimal("0.00"),
            invoice_status="CONFIRMED",
            allocation_amount=Decimal("500.00"),
            payment_customer_id=1,
            invoice_customer_id=1,
        )
    assert "Cannot allocate payment with status 'CANCELLED'" in str(exc.value)


def test_cancelled_invoice_cannot_receive_allocation() -> None:
    """Scenario 10: Cancelled or voided invoices reject allocations."""
    with pytest.raises(InvalidInvoiceStateError):
        payment_allocation_service.validate_allocation_eligibility(
            payment_amount=Decimal("1000.00"),
            payment_allocated=Decimal("0.00"),
            payment_status="SUCCESS",
            invoice_total=Decimal("500.00"),
            invoice_paid=Decimal("0.00"),
            invoice_status="CANCELLED",
            allocation_amount=Decimal("500.00"),
            payment_customer_id=1,
            invoice_customer_id=1,
        )


def test_reversed_allocation_restores_balances() -> None:
    """Scenario 11: Reversing an allocation restores invoice balance and unallocated payment amount."""
    new_paid, balance_due, new_allocated = payment_allocation_service.calculate_new_balances(
        current_invoice_total=Decimal("1000.00"),
        current_invoice_paid=Decimal("600.00"),
        current_payment_allocated=Decimal("600.00"),
        allocation_amount=Decimal("200.00"),
        is_reversal=True,
    )
    assert new_paid == Decimal("400.00")
    assert balance_due == Decimal("600.00")
    assert new_allocated == Decimal("400.00")


def test_accurate_overdue_status_determination() -> None:
    """Scenario 12: Accurate overdue status derivation based on balance and due date."""
    # Invoice partially paid but overdue
    status_overdue = payment_allocation_service.derive_invoice_status(
        total_amount=Decimal("1000.00"),
        amount_paid=Decimal("400.00"),
        is_overdue=True,
    )
    assert status_overdue == "OVERDUE"

    # Invoice fully paid is always PAID even if past due date
    status_paid = payment_allocation_service.derive_invoice_status(
        total_amount=Decimal("1000.00"),
        amount_paid=Decimal("1000.00"),
        is_overdue=True,
    )
    assert status_paid == "PAID"
