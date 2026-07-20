"""Date utilities for the rule engine."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def parse_date(value: str | datetime | None) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    for fmt in (
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ):
        try:
            dt = datetime.strptime(value.replace("Z", "+00:00"), fmt)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def days_ago(n: int) -> datetime:
    return utcnow() - timedelta(days=n)


def months_ago(n: int) -> datetime:
    now = utcnow()
    month = now.month - n
    year = now.year + month // 12
    month = month % 12 or 12
    return now.replace(year=year, month=month)


def days_until(dt: datetime) -> int:
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return (dt - utcnow()).days


def age_in_years(dt: datetime) -> float:
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return (utcnow() - dt).days / 365.25


def age_in_days(dt: datetime) -> int:
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return (utcnow() - dt).days


def format_period(dt: datetime, period: str = "month") -> str:
    """period: 'day' | 'week' | 'month' | 'quarter' | 'year'"""
    if period == "day":
        return dt.strftime("%Y-%m-%d")
    elif period == "week":
        iso = dt.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    elif period == "month":
        return dt.strftime("%Y-%m")
    elif period == "quarter":
        q = (dt.month - 1) // 3 + 1
        return f"{dt.year}-Q{q}"
    return str(dt.year)


def date_range_periods(start: datetime, end: datetime, period: str = "month") -> list[str]:
    """Generate all period labels from start to end inclusive."""
    periods: list[str] = []
    current = start.replace(day=1) if period in ("month", "quarter") else start
    while current <= end:
        periods.append(format_period(current, period))
        if period == "day":
            current += timedelta(days=1)
        elif period == "week":
            current += timedelta(weeks=1)
        elif period == "month":
            m = current.month + 1
            y = current.year + (m - 1) // 12
            m = (m - 1) % 12 + 1
            current = current.replace(year=y, month=m, day=1)
        elif period == "quarter":
            m = current.month + 3
            y = current.year + (m - 1) // 12
            m = (m - 1) % 12 + 1
            current = current.replace(year=y, month=m, day=1)
        else:
            current = current.replace(year=current.year + 1)
    return periods


def is_expired(dt: datetime, ttl_seconds: float) -> bool:
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return (utcnow() - dt).total_seconds() > ttl_seconds


def deadline_urgency(deadline: datetime) -> str:
    """Returns 'critical' | 'high' | 'medium' | 'low' | 'expired'."""
    d = days_until(deadline)
    if d < 0:
        return "expired"
    if d <= 3:
        return "critical"
    if d <= 14:
        return "high"
    if d <= 30:
        return "medium"
    return "low"
