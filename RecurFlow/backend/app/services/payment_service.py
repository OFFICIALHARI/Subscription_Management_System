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
    CustomerMismatchError,
    InvalidInvoiceStateError,
    InvoiceOverPaymentError,
    OverAllocationError,
    payment_allocation_service,
)
from app.services.pricing_service import round_currency


class PaymentService:
    """Handles payment receipt, allocation against invoices, and account reconciliation."""

    def _generate_payment_reference(self, db: Session) -> str:
        current_year = date.today().year
        count = (
            db.query(func.count(Payment.id))
            .filter(Payment.payment_reference.like(f"PAY-{current_year}-%"))
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
        return query.order_by(Payment.payment_date.desc(), Payment.created_at.desc()).offset(skip).limit(limit).all()

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
        ref = self._generate_payment_reference(db)
        payment_date = payment_in.payment_date or date.today()

        payment = Payment(
            payment_reference=ref,
            customer_id=payment_in.customer_id,
            amount=payment_in.amount,
            currency=payment_in.currency,
            payment_method=payment_in.payment_method.upper(),
            payment_date=payment_date,
            status="COMPLETED",
            amount_allocated=Decimal("0.00"),
            unallocated_balance=payment_in.amount,
            notes=payment_in.notes,
        )
        db.add(payment)
        db.flush()

        # If specific invoice provided, attempt allocation
        if payment_in.invoice_id:
            invoice = db.query(Invoice).filter(Invoice.id == payment_in.invoice_id).first()
            if invoice:
                alloc_amount = min(payment.unallocated_balance, invoice.balance_due)
                if alloc_amount > Decimal("0.00"):
                    self.allocate_payment(
                        db=db,
                        payment_id=payment.id,
                        invoice_id=invoice.id,
                        amount=alloc_amount,
                    )

        db.commit()
        db.refresh(payment)
        return payment

    def allocate_payment(
        self, db: Session, payment_id: int, invoice_id: int, amount: Decimal
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
            # 1. Customer boundary validation
            payment_allocation_service.validate_customer_boundary(
                payment_customer_id=payment.customer_id,
                invoice_customer_id=invoice.customer_id,
            )

            # 2. Invoice eligibility validation
            payment_allocation_service.validate_invoice_eligibility(
                invoice_status=invoice.status,
                invoice_balance_due=invoice.balance_due,
            )

            # 3. Allocation bounds validation
            payment_allocation_service.validate_allocation_bounds(
                requested_amount=amount,
                unallocated_payment_balance=payment.unallocated_balance,
                invoice_balance_due=invoice.balance_due,
            )
        except (
            CustomerMismatchError,
            InvalidInvoiceStateError,
            OverAllocationError,
            InvoiceOverPaymentError,
        ) as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(err),
            )

        # 4. Calculate new ledger balances
        new_paid, new_balance_due, new_allocated = payment_allocation_service.calculate_new_balances(
            current_invoice_total=invoice.total_amount,
            current_invoice_paid=invoice.amount_paid,
            current_payment_amount=payment.amount,
            current_payment_allocated=payment.amount_allocated,
            allocation_amount=amount,
        )

        # 5. Create allocation ledger entry
        allocation = PaymentAllocation(
            payment_id=payment.id,
            invoice_id=invoice.id,
            allocated_amount=amount,
            allocation_date=datetime.now(UTC),
        )
        db.add(allocation)

        # 6. Update invoice state
        invoice.amount_paid = new_paid
        invoice.balance_due = new_balance_due
        if new_balance_due == Decimal("0.00"):
            invoice.status = "PAID"
            invoice.paid_at = datetime.now(UTC)
        elif new_paid > Decimal("0.00"):
            invoice.status = "PARTIALLY_PAID"

        # 7. Update payment balance
        payment.amount_allocated = new_allocated
        payment.unallocated_balance = round_currency(payment.amount - new_allocated)

        db.commit()
        db.refresh(allocation)
        return allocation


payment_service = PaymentService()
