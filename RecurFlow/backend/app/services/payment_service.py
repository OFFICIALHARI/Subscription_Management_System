"""Payment recording, ledger allocation, and invoice reconciliation service."""

from datetime import UTC, date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.models.invoice import Invoice
from app.models.payment import Payment, PaymentAllocation
from app.schemas.payment import PaymentCreate
from app.services.payment_allocation_service import (
    AllocationError,
    CustomerMismatchError,
    InvalidInvoiceStateError,
    InvoiceOverPaymentError,
    OverAllocationError,
    payment_allocation_service,
)
from app.services.pricing_service import round_currency

ALLOWED_METHODS = {"BANK_TRANSFER", "CHEQUE", "CASH", "MANUAL_OTHER"}


class PaymentService:
    """Handles payment receipt, allocation against invoices, and account reconciliation."""

    def _generate_payment_number(self, db: Session) -> str:
        current_year = date.today().year
        count = (
            db.query(func.count(Payment.id))
            .filter(Payment.payment_number.like(f"PAY-{current_year}-%"))
            .scalar()
            or 0
        )
        return f"PAY-{current_year}-{count + 1:05d}"

    def list_payments(
        self,
        db: Session,
        customer_id: int | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Payment]:
        query = db.query(Payment).options(joinedload(Payment.allocations))
        if customer_id is not None:
            query = query.filter(Payment.customer_id == customer_id)
        return (
            query.order_by(Payment.paid_at.desc(), Payment.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_payment(self, db: Session, payment_id: int) -> Payment:
        pay = (
            db.query(Payment)
            .options(joinedload(Payment.allocations))
            .filter(Payment.id == payment_id)
            .first()
        )
        if not pay:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Payment with ID {payment_id} not found.",
            )
        return pay

    def create_payment(self, db: Session, payment_in: PaymentCreate) -> Payment:
        """Register a received payment, with optional immediate allocation to an invoice."""
        method = payment_in.payment_method.upper()
        if method == "MANUAL":
            method = "MANUAL_OTHER"
        if method not in ALLOWED_METHODS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "payment_method must be one of BANK_TRANSFER, CHEQUE, CASH, or MANUAL_OTHER."
                ),
            )
        paid_at = payment_in.paid_at or date.today()

        payment = Payment(
            payment_number=self._generate_payment_number(db),
            customer_id=payment_in.customer_id,
            amount=payment_in.amount,
            currency=payment_in.currency.upper(),
            payment_method=method,
            paid_at=paid_at,
            transaction_reference=payment_in.transaction_reference,
            status="SUCCESS",
            amount_allocated=Decimal("0.00"),
            notes=payment_in.notes,
        )
        db.add(payment)
        db.flush()

        if payment_in.invoice_id:
            invoice = db.query(Invoice).filter(Invoice.id == payment_in.invoice_id).first()
            if not invoice:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Invoice with ID {payment_in.invoice_id} not found.",
                )
            unallocated = payment.amount - payment.amount_allocated
            alloc_amount = min(unallocated, invoice.balance_due)
            if alloc_amount > Decimal("0.00"):
                self.allocate_payment(
                    db=db,
                    payment_id=payment.id,
                    invoice_id=invoice.id,
                    amount=alloc_amount,
                    commit=False,
                )

        db.commit()
        db.refresh(payment)
        return payment

    def allocate_payment(
        self,
        db: Session,
        payment_id: int,
        invoice_id: int,
        amount: Decimal,
        commit: bool = True,
    ) -> PaymentAllocation:
        """Allocate amount from payment unallocated balance to invoice."""
        payment = self.get_payment(db, payment_id)
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice with ID {invoice_id} not found.",
            )

        try:
            payment_allocation_service.validate_allocation_eligibility(
                payment_amount=payment.amount,
                payment_allocated=payment.amount_allocated,
                payment_status=payment.status,
                invoice_total=invoice.total_amount,
                invoice_paid=invoice.amount_paid,
                invoice_status=invoice.status,
                allocation_amount=amount,
                payment_customer_id=payment.customer_id,
                invoice_customer_id=invoice.customer_id,
            )
        except (
            CustomerMismatchError,
            InvalidInvoiceStateError,
            OverAllocationError,
            InvoiceOverPaymentError,
            AllocationError,
        ) as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            ) from err

        new_paid, new_balance_due, new_allocated = payment_allocation_service.calculate_new_balances(
            current_invoice_total=invoice.total_amount,
            current_invoice_paid=invoice.amount_paid,
            current_payment_allocated=payment.amount_allocated,
            allocation_amount=amount,
        )

        allocation = PaymentAllocation(
            payment_id=payment.id,
            invoice_id=invoice.id,
            allocated_amount=amount,
            allocated_at=datetime.now(UTC),
        )
        db.add(allocation)

        invoice.amount_paid = new_paid
        invoice.balance_due = new_balance_due
        invoice.status = payment_allocation_service.derive_invoice_status(
            total_amount=invoice.total_amount,
            amount_paid=new_paid,
            is_overdue=invoice.due_date < date.today() and new_balance_due > Decimal("0.00"),
        )

        payment.amount_allocated = new_allocated

        if commit:
            db.commit()
            db.refresh(allocation)
        else:
            db.flush()
        return allocation


payment_service = PaymentService()
