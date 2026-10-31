"""Centralized billing cycle and date arithmetic service for RecurFlow."""

import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Literal

BillingIntervalType = Literal["DAILY", "WEEKLY", "MONTHLY", "YEARLY"]


class BillingDateService:
    """Authoritative service for computing recurring billing dates and cycle boundaries."""

    @staticmethod
    def get_days_in_month(year: int, month: int) -> int:
        """Return the number of days in the specified year and month."""
        return calendar.monthrange(year, month)[1]

    @staticmethod
    def is_leap_year(year: int) -> bool:
        """Return True if year is a leap year."""
        return calendar.isleap(year)

    @classmethod
    def calculate_next_monthly_date(
        cls,
        current_date: date,
        anchor_day: int,
        interval_count: int = 1,
    ) -> date:
        """
        Calculate next monthly billing date from current_date using the immutable anchor_day.
        Clamps to the last day of shorter months (e.g. Feb 28/29, April 30) while preserving
        the original anchor_day for future cycles.
        """
        total_months = (current_date.month - 1) + interval_count
        target_year = current_date.year + (total_months // 12)
        target_month = (total_months % 12) + 1

        max_days = cls.get_days_in_month(target_year, target_month)
        clamped_day = min(anchor_day, max_days)
        return date(target_year, target_month, clamped_day)

    @classmethod
    def calculate_next_yearly_date(
        cls,
        current_date: date,
        anchor_day: int,
        anchor_month: int = 1,
        interval_count: int = 1,
    ) -> date:
        """
        Calculate next yearly billing date. Handles leap years (Feb 29) gracefully:
        in non-leap years, bills on Feb 28; in leap years, bills on Feb 29.
        """
        target_year = current_date.year + interval_count
        max_days = cls.get_days_in_month(target_year, anchor_month)
        clamped_day = min(anchor_day, max_days)
        return date(target_year, anchor_month, clamped_day)

    @classmethod
    def calculate_next_billing_date(
        cls,
        current_date: date,
        interval: BillingIntervalType,
        interval_count: int = 1,
        anchor_day: int | None = None,
        anchor_month: int | None = None,
    ) -> date:
        """Authoritative dispatcher for computing next billing date across all frequencies."""
        if interval_count < 1:
            raise ValueError("interval_count must be at least 1")

        if interval == "DAILY":
            return current_date + timedelta(days=interval_count)

        if interval == "WEEKLY":
            return current_date + timedelta(days=7 * interval_count)

        if interval == "MONTHLY":
            anchor = anchor_day if anchor_day is not None else current_date.day
            return cls.calculate_next_monthly_date(current_date, anchor_day=anchor, interval_count=interval_count)

        if interval == "YEARLY":
            anchor_d = anchor_day if anchor_day is not None else current_date.day
            anchor_m = anchor_month if anchor_month is not None else current_date.month
            return cls.calculate_next_yearly_date(
                current_date, anchor_day=anchor_d, anchor_month=anchor_m, interval_count=interval_count
            )

        raise ValueError(f"Unsupported billing interval: {interval}")

    @classmethod
    def compute_billing_period(
        cls,
        period_start: date,
        interval: BillingIntervalType,
        interval_count: int = 1,
        anchor_day: int | None = None,
    ) -> tuple[date, date]:
        """
        Returns semi-open interval [period_start, period_end).
        period_end is the start of the subsequent period.
        """
        period_end = cls.calculate_next_billing_date(
            current_date=period_start,
            interval=interval,
            interval_count=interval_count,
            anchor_day=anchor_day,
            anchor_month=period_start.month,
        )
        return period_start, period_end

    @classmethod
    def calculate_resumption_date(
        cls,
        scheduled_next_date: date,
        paused_at: datetime | date,
        resumed_at: datetime | date,
        anchor_day: int | None = None,
    ) -> date:
        """
        Adjusts scheduled_next_date after a pause by shifting it forward by the
        elapsed paused days if paused before the scheduled billing date.
        """
        paused_d = paused_at.date() if isinstance(paused_at, datetime) else paused_at
        resumed_d = resumed_at.date() if isinstance(resumed_at, datetime) else resumed_at

        pause_duration_days = max(1, (resumed_d - paused_d).days)

        if paused_d < scheduled_next_date:
            # Shift scheduled date forward by the exact pause duration
            return scheduled_next_date + timedelta(days=pause_duration_days)

        # If already overdue during pause, restart from resumption date
        return resumed_d


billing_date_service = BillingDateService()
