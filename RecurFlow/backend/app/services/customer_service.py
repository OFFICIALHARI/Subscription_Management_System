"""Customer management domain service."""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.models.invoice import Invoice
from app.models.subscription import Subscription
from app.schemas.customer import CustomerCreate, CustomerDetailResponse, CustomerUpdate


class CustomerService:
    """Customer CRUD and relation metrics service."""

    def list_customers(
        self,
        db: Session,
        search: str | None = None,
        is_active: bool | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Customer]:
        """Query customers with optional search and filter."""
        query = db.query(Customer)
        if is_active is not None:
            query = query.filter(Customer.is_active == is_active)
        if search:
            pattern = f"%{search}%"
            query = query.filter(
                (Customer.company_name.ilike(pattern))
                | (Customer.contact_name.ilike(pattern))
                | (Customer.email.ilike(pattern))
            )
        return query.order_by(Customer.company_name.asc()).offset(skip).limit(limit).all()

    def get_customer(self, db: Session, customer_id: int) -> Customer:
        """Fetch customer by ID or 404."""
        customer = db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Customer with ID {customer_id} not found.",
            )
        return customer

    def get_customer_detail(self, db: Session, customer_id: int) -> CustomerDetailResponse:
        """Fetch customer by ID with aggregated financial and subscription metrics."""
        customer = self.get_customer(db, customer_id)

        active_subs = (
            db.query(func.count(Subscription.id))
            .filter(
                Subscription.customer_id == customer_id,
                Subscription.status == "ACTIVE",
            )
            .scalar()
            or 0
        )

        invoices_agg = (
            db.query(
                func.coalesce(func.sum(Invoice.total_amount), 0),
                func.coalesce(func.sum(Invoice.balance_due), 0),
            )
            .filter(Invoice.customer_id == customer_id, Invoice.status != "CANCELLED")
            .first()
        )

        total_invoiced = float(invoices_agg[0]) if invoices_agg else 0.0
        outstanding = float(invoices_agg[1]) if invoices_agg else 0.0

        return CustomerDetailResponse(
            id=customer.id,
            user_id=customer.user_id,
            company_name=customer.company_name,
            contact_name=customer.contact_name,
            email=customer.email,
            phone=customer.phone,
            tax_identifier=customer.tax_identifier,
            billing_address_line1=customer.billing_address_line1,
            billing_address_line2=customer.billing_address_line2,
            billing_city=customer.billing_city,
            billing_state=customer.billing_state,
            billing_postal_code=customer.billing_postal_code,
            billing_country=customer.billing_country,
            is_active=customer.is_active,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
            active_subscriptions_count=active_subs,
            total_invoiced_amount=total_invoiced,
            outstanding_balance=outstanding,
        )

    def create_customer(self, db: Session, customer_in: CustomerCreate) -> Customer:
        """Create a new customer."""
        existing = db.query(Customer).filter(Customer.email == str(customer_in.email).lower()).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A customer with email '{customer_in.email}' already exists.",
            )
        customer = Customer(
            user_id=customer_in.user_id,
            company_name=customer_in.company_name,
            contact_name=customer_in.contact_name,
            email=str(customer_in.email).lower(),
            phone=customer_in.phone,
            tax_identifier=customer_in.tax_identifier,
            billing_address_line1=customer_in.billing_address_line1,
            billing_address_line2=customer_in.billing_address_line2,
            billing_city=customer_in.billing_city,
            billing_state=customer_in.billing_state,
            billing_postal_code=customer_in.billing_postal_code,
            billing_country=customer_in.billing_country,
            is_active=True,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer

    def update_customer(
        self, db: Session, customer_id: int, customer_in: CustomerUpdate
    ) -> Customer:
        """Update customer details."""
        customer = self.get_customer(db, customer_id)
        update_data = customer_in.model_dump(exclude_unset=True)
        if "email" in update_data and update_data["email"] is not None:
            update_data["email"] = str(update_data["email"]).lower()
            clash = (
                db.query(Customer)
                .filter(Customer.email == update_data["email"], Customer.id != customer_id)
                .first()
            )
            if clash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A customer with email '{update_data['email']}' already exists.",
                )
        for field, value in update_data.items():
            setattr(customer, field, value)
        db.commit()
        db.refresh(customer)
        return customer

    def delete_customer(self, db: Session, customer_id: int) -> Customer:
        """Soft-deactivate customer."""
        customer = self.get_customer(db, customer_id)
        customer.is_active = False
        db.commit()
        db.refresh(customer)
        return customer


customer_service = CustomerService()
