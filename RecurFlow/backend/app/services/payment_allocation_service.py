"""Payment allocation domain service for RecurFlow."""

from decimal import Decimal
from typing import Any


class AllocationError(Exception):
    """Base exception for payment allocation failures."""
    pass


class OverAllocationError(AllocationError):
    """Raised when an allocation exceeds the available payment balance."""
    pass


class InvoiceOverPaymentError(AllocationError):
    """Raised when an allocation exceeds the outstanding invoice balance."""
    pass


class CustomerMismatchError(AllocationError):
    """Raised when a payment and invoice belong to different customers."""
    pass


class InvalidInvoiceStateError(AllocationError):
    """Raised when attempting to allocate to a cancelled or voided invoice."""
    pass


class AllocationReversalError(AllocationError):
    """Raised when an allocation reversal is invalid."""
    pass


class PaymentAllocationService:
    """Service encapsulating pure financial rules and verification for payment allocations."""

    @staticmethod
    def to_decimal(val: Any) -> Decimal:
        """Convert input to 2-decimal rounded Decimal."""
        return Decimal(str(val)).quantize(Decimal("0.01"))

    @classmethod
    def validate_allocation_eligibility(
        cls,
        payment_amount: Decimal,
        payment_allocated: Decimal,
        payment_status: str,
        invoice_total: Decimal,
        invoice_paid: Decimal,
        invoice_status: str,
        allocation_amount: Decimal,
        payment_customer_id: int,
        invoice_customer_id: int,
    ) -> None:
        """Validate all financial and authorization invariants before an allocation."""
        alloc_dec = cls.to_decimal(allocation_amount)
        if alloc_dec <= Decimal("0.00"):
            raise AllocationError("Allocation amount must be strictly greater than zero.")

        if payment_status != "SUCCESS":
            raise AllocationError(f"Cannot allocate payment with status '{payment_status}'. Only 'SUCCESS' allowed.")

        if invoice_status in ("CANCELLED", "DRAFT"):
            raise InvalidInvoiceStateError(f"Cannot allocate to invoice with status '{invoice_status}'.")

        if payment_customer_id != invoice_customer_id:
            raise CustomerMismatchError(
                f"Customer mismatch: Payment customer ({payment_customer_id}) does not match Invoice customer ({invoice_customer_id})."
            )

        pay_amount = cls.to_decimal(payment_amount)
        pay_allocated = cls.to_decimal(payment_allocated)
        unallocated_payment = pay_amount - pay_allocated

        if alloc_dec > unallocated_payment:
            raise OverAllocationError(
                f"Attempted to allocate {alloc_dec}, but only {unallocated_payment} unallocated balance remains on payment."
            )

        inv_total = cls.to_decimal(invoice_total)
        inv_paid = cls.to_decimal(invoice_paid)
        balance_due = inv_total - inv_paid

        if alloc_dec > balance_due:
            raise InvoiceOverPaymentError(
                f"Attempted to allocate {alloc_dec}, but invoice balance due is only {balance_due}."
            )

    @classmethod
    def calculate_new_balances(
        cls,
        current_invoice_total: Decimal,
        current_invoice_paid: Decimal,
        current_payment_allocated: Decimal,
        allocation_amount: Decimal,
        is_reversal: bool = False,
    ) -> tuple[Decimal, Decimal, Decimal]:
        """
        Calculates new (invoice_amount_paid, invoice_balance_due, payment_amount_allocated).
        Supports both allocation and allocation reversal.
        """
        inv_total = cls.to_decimal(current_invoice_total)
        inv_paid = cls.to_decimal(current_invoice_paid)
        pay_allocated = cls.to_decimal(current_payment_allocated)
        amount = cls.to_decimal(allocation_amount)

        if not is_reversal:
            new_inv_paid = inv_paid + amount
            new_pay_allocated = pay_allocated + amount
        else:
            if amount > inv_paid:
                raise AllocationReversalError("Cannot reverse more than total paid amount on invoice.")
            if amount > pay_allocated:
                raise AllocationReversalError("Cannot reverse more than total allocated on payment.")
            new_inv_paid = inv_paid - amount
            new_pay_allocated = pay_allocated - amount

        new_balance_due = inv_total - new_inv_paid
        return new_inv_paid, new_balance_due, new_pay_allocated

    @classmethod
    def derive_invoice_status(
        cls,
        total_amount: Decimal,
        amount_paid: Decimal,
        is_overdue: bool = False,
    ) -> str:
        """Derive standard invoice state from balances and temporal status."""
        total = cls.to_decimal(total_amount)
        paid = cls.to_decimal(amount_paid)

        if paid == Decimal("0.00"):
            return "OVERDUE" if is_overdue else "CONFIRMED"
        if paid == total:
            return "PAID"
        if Decimal("0.00") < paid < total:
            return "OVERDUE" if is_overdue else "PARTIALLY_PAID"

        raise AllocationError("Invalid balance state: amount_paid exceeds total_amount.")


payment_allocation_service = PaymentAllocationService()
