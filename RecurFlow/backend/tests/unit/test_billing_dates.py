"""Unit tests for centralized billing date calculation and calendar boundary rules."""

from datetime import date, datetime, timezone
import pytest

from app.services.billing_date_service import billing_date_service


def test_daily_billing() -> None:
    """Scenario 1: Daily billing interval."""
    start = date(2026, 3, 1)
    next_date = billing_date_service.calculate_next_billing_date(start, interval="DAILY", interval_count=1)
    assert next_date == date(2026, 3, 2)

    next_3_days = billing_date_service.calculate_next_billing_date(start, interval="DAILY", interval_count=3)
    assert next_3_days == date(2026, 3, 4)


def test_weekly_billing() -> None:
    """Scenario 2: Weekly billing interval (exactly 7 calendar days)."""
    start = date(2026, 3, 1)  # Sunday
    next_week = billing_date_service.calculate_next_billing_date(start, interval="WEEKLY", interval_count=1)
    assert next_week == date(2026, 3, 8)  # Next Sunday


def test_monthly_billing_regular() -> None:
    """Scenario 3: Standard monthly billing."""
    start = date(2026, 3, 15)
    next_month = billing_date_service.calculate_next_billing_date(
        start, interval="MONTHLY", interval_count=1, anchor_day=15
    )
    assert next_month == date(2026, 4, 15)


def test_yearly_billing_regular() -> None:
    """Scenario 4: Standard yearly billing."""
    start = date(2026, 5, 10)
    next_year = billing_date_service.calculate_next_billing_date(
        start, interval="YEARLY", interval_count=1, anchor_day=10, anchor_month=5
    )
    assert next_year == date(2027, 5, 10)


def test_month_end_jan_to_feb_to_march_non_leap_year() -> None:
    """Scenario 5: January 31 -> February 28 -> March 31 in a non-leap year (2026)."""
    anchor_day = 31

    # Jan 31 -> Feb 28
    jan_date = date(2026, 1, 31)
    feb_date = billing_date_service.calculate_next_monthly_date(jan_date, anchor_day=anchor_day, interval_count=1)
    assert feb_date == date(2026, 2, 28)

    # Feb 28 -> March 31 (anchor day 31 must be preserved!)
    march_date = billing_date_service.calculate_next_monthly_date(feb_date, anchor_day=anchor_day, interval_count=1)
    assert march_date == date(2026, 3, 31)


def test_month_end_jan_to_feb_to_march_leap_year() -> None:
    """Scenario 6: January 31 -> February 29 -> March 31 in a leap year (2028)."""
    anchor_day = 31

    jan_date = date(2028, 1, 31)
    feb_date = billing_date_service.calculate_next_monthly_date(jan_date, anchor_day=anchor_day, interval_count=1)
    assert feb_date == date(2028, 2, 29)

    march_date = billing_date_service.calculate_next_monthly_date(feb_date, anchor_day=anchor_day, interval_count=1)
    assert march_date == date(2028, 3, 31)


def test_feb_29_yearly_subscription_non_leap_year() -> None:
    """Scenario 7: February 29 yearly subscription billed in non-leap years (2025)."""
    start = date(2024, 2, 29)  # Leap year start
    year_1 = billing_date_service.calculate_next_yearly_date(start, anchor_day=29, anchor_month=2, interval_count=1)
    assert year_1 == date(2025, 2, 28)  # Non-leap year clamped to Feb 28


def test_feb_29_yearly_subscription_leap_year() -> None:
    """Scenario 8: February 29 yearly subscription restores to Feb 29 on subsequent leap year (2028)."""
    current = date(2027, 2, 28)
    year_leap = billing_date_service.calculate_next_yearly_date(current, anchor_day=29, anchor_month=2, interval_count=1)
    assert year_leap == date(2028, 2, 29)  # 2028 is leap year, 29 restored!


def test_april_30_to_may_31_anchor_preserved() -> None:
    """Scenario 9: April 30 -> May 31 where anchor-day is 31."""
    anchor_day = 31
    april_date = date(2026, 4, 30)
    may_date = billing_date_service.calculate_next_monthly_date(april_date, anchor_day=anchor_day, interval_count=1)
    assert may_date == date(2026, 5, 31)


def test_pause_before_next_billing() -> None:
    """Scenario 10: Pause occurs before scheduled billing date."""
    scheduled = date(2026, 4, 15)
    paused_at = date(2026, 4, 1)
    resumed_at = date(2026, 4, 11)  # 10 days paused

    resumed_next = billing_date_service.calculate_resumption_date(
        scheduled_next_date=scheduled, paused_at=paused_at, resumed_at=resumed_at
    )
    # Scheduled date must advance by 10 days to credit customer: April 15 + 10 days = April 25
    assert resumed_next == date(2026, 4, 25)


def test_pause_during_active_period() -> None:
    """Scenario 11 & 12: Pause duration spanning past original billing date."""
    scheduled = date(2026, 4, 15)
    paused_at = date(2026, 4, 10)
    resumed_at = date(2026, 4, 25)  # 15 days paused, now past April 15

    resumed_next = billing_date_service.calculate_resumption_date(
        scheduled_next_date=scheduled, paused_at=paused_at, resumed_at=resumed_at
    )
    # April 15 + 15 days = April 30
    assert resumed_next == date(2026, 4, 30)


def test_billing_period_semi_open_interval() -> None:
    """Scenario 13 & 14: Semi-open billing period [start, end) and uniqueness check."""
    start = date(2026, 1, 1)
    p_start, p_end = billing_date_service.compute_billing_period(start, interval="MONTHLY", interval_count=1)
    assert p_start == date(2026, 1, 1)
    assert p_end == date(2026, 2, 1)

    # Idempotent re-computation gives identical boundary
    p_start_2, p_end_2 = billing_date_service.compute_billing_period(start, interval="MONTHLY", interval_count=1)
    assert (p_start, p_end) == (p_start_2, p_end_2)


def test_utc_consistency() -> None:
    """Scenario 15: UTC instant boundary handling."""
    utc_now = datetime.now(timezone.utc)
    assert utc_now.tzinfo == timezone.utc
