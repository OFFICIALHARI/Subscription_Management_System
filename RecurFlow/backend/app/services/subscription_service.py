"""Subscription domain service, lifecycle state machine, pause/resume, and renewal."""

from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.plan import Plan
from app.models.subscription import Subscription, SubscriptionEvent
from app.services.billing_date_service import billing_date_service


def _plan_for(db: Session, sub: Subscription) -> Plan:
    plan = sub.plan if sub.__dict__.get("plan") is not None else None
    if plan is None:
        plan = db.query(Plan).filter(Plan.id == sub.plan_id).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Subscription {sub.subscription_number} is missing its billing plan.",
        )
    return plan


class SubscriptionService:
    """Manages subscription state transitions, pause/resume rules, and renewals."""

    def list_subscriptions(
        self,
        db: Session,
        customer_id: int | None = None,
        status_filter: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Subscription]:
        query = db.query(Subscription).options(
            joinedload(Subscription.lines), joinedload(Subscription.plan)
        )
        if customer_id is not None:
            query = query.filter(Subscription.customer_id == customer_id)
        if status_filter:
            query = query.filter(Subscription.status == status_filter.upper())
        return query.order_by(Subscription.created_at.desc()).offset(skip).limit(limit).all()

    def get_subscription(self, db: Session, subscription_id: int) -> Subscription:
        sub = (
            db.query(Subscription)
            .options(
                joinedload(Subscription.lines),
                joinedload(Subscription.events),
                joinedload(Subscription.plan),
            )
            .filter(Subscription.id == subscription_id)
            .first()
        )
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription with ID {subscription_id} not found.",
            )
        return sub

    def pause_subscription(
        self, db: Session, subscription_id: int, reason: str | None = None
    ) -> Subscription:
        """Pause an active subscription."""
        sub = self.get_subscription(db, subscription_id)
        if sub.status != "ACTIVE":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause subscription with status '{sub.status}'. Must be 'ACTIVE'.",
            )

        now = datetime.now(UTC)
        sub.status = "PAUSED"
        sub.paused_at = now

        event = SubscriptionEvent(
            subscription_id=sub.id,
            event_type="PAUSED",
            from_status="ACTIVE",
            to_status="PAUSED",
            reason=reason or "Subscription paused by operator request.",
        )
        db.add(event)
        db.commit()
        db.refresh(sub)
        return sub

    def resume_subscription(
        self, db: Session, subscription_id: int, notes: str | None = None
    ) -> Subscription:
        """Resume a paused subscription."""
        sub = self.get_subscription(db, subscription_id)
        if sub.status != "PAUSED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot resume subscription with status '{sub.status}'. Must be 'PAUSED'.",
            )

        now = datetime.now(UTC)
        plan = _plan_for(db, sub)
        sub.status = "ACTIVE"
        sub.resumed_at = now

        today = date.today()
        if sub.next_billing_date <= today:
            next_date = billing_date_service.calculate_next_billing_date(
                current_date=today,
                interval=plan.billing_interval,  # type: ignore[arg-type]
                interval_count=plan.interval_count,
                anchor_day=sub.billing_anchor_day,
                anchor_month=sub.start_date.month,
            )
            sub.next_billing_date = next_date

        event = SubscriptionEvent(
            subscription_id=sub.id,
            event_type="RESUMED",
            from_status="PAUSED",
            to_status="ACTIVE",
            reason=notes or "Subscription resumed.",
        )
        db.add(event)
        db.commit()
        db.refresh(sub)
        return sub

    def renew_subscription(
        self, db: Session, subscription_id: int, notes: str | None = None
    ) -> Subscription:
        """Explicitly renew or extend the subscription billing date."""
        sub = self.get_subscription(db, subscription_id)
        if sub.status not in ["ACTIVE", "PAUSED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot renew subscription in state '{sub.status}'.",
            )

        plan = _plan_for(db, sub)
        prev_status = sub.status
        new_next = billing_date_service.calculate_next_billing_date(
            current_date=sub.next_billing_date,
            interval=plan.billing_interval,  # type: ignore[arg-type]
            interval_count=plan.interval_count,
            anchor_day=sub.billing_anchor_day,
            anchor_month=sub.start_date.month,
        )
        sub.next_billing_date = new_next
        sub.status = "ACTIVE"

        event = SubscriptionEvent(
            subscription_id=sub.id,
            event_type="RENEWED",
            from_status=prev_status,
            to_status="ACTIVE",
            reason=notes or "Subscription period extended / renewed.",
        )
        db.add(event)
        db.commit()
        db.refresh(sub)
        return sub

    def close_subscription(
        self, db: Session, subscription_id: int, reason: str
    ) -> Subscription:
        """Cancel and close subscription."""
        sub = self.get_subscription(db, subscription_id)
        if sub.status == "CLOSED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Subscription is already closed.",
            )

        prev_status = sub.status
        sub.status = "CLOSED"
        sub.end_date = date.today()
        sub.auto_close_reason = reason

        event = SubscriptionEvent(
            subscription_id=sub.id,
            event_type="CLOSED",
            from_status=prev_status,
            to_status="CLOSED",
            reason=f"Subscription closed: {reason}",
        )
        db.add(event)
        db.commit()
        db.refresh(sub)
        return sub


subscription_service = SubscriptionService()
