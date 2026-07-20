"""Threshold-based deterministic alert generation — no AI required."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..utils.date_utils import days_until, parse_date, age_in_days


@dataclass
class Alert:
    code: str
    level: str          # 'info' | 'warning' | 'critical'
    title: str
    message: str
    category: str       # 'profile' | 'publications' | 'grants' | 'account' | 'security' | 'activity'
    action: str = ""
    action_url: str = ""
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "level": self.level,
            "title": self.title,
            "message": self.message,
            "category": self.category,
            "action": self.action,
            "action_url": self.action_url,
            "data": self.data,
        }


def generate_profile_alerts(profile: dict) -> list[Alert]:
    alerts: list[Alert] = []

    if not profile.get("orcid_id"):
        alerts.append(Alert(
            code="ORCID_DISCONNECTED", level="warning", category="profile",
            title="ORCID iD not connected",
            message="Connect your ORCID iD to verify your identity and auto-import publications.",
            action="Connect ORCID", action_url="/profile/settings#orcid",
        ))

    bio = profile.get("bio") or ""
    if len(bio) < 50:
        alerts.append(Alert(
            code="PROFILE_MISSING_BIO", level="info", category="profile",
            title="Profile biography missing",
            message="Add a biography to improve your discoverability by collaborators.",
            action="Add bio", action_url="/profile/edit",
        ))

    keywords = profile.get("research_keywords") or []
    if len(keywords) < 3:
        alerts.append(Alert(
            code="PROFILE_FEW_KEYWORDS", level="info", category="profile",
            title="Too few research keywords",
            message=f"You have {len(keywords)} keyword(s). Add at least 3 to improve matching.",
            action="Add keywords", action_url="/profile/edit",
        ))

    if not profile.get("institution"):
        alerts.append(Alert(
            code="PROFILE_MISSING_INSTITUTION", level="warning", category="profile",
            title="Institution not set",
            message="Add your institution to participate in institution-wide analytics and grants.",
            action="Add institution", action_url="/profile/edit",
        ))

    return alerts


def generate_publication_alerts(
    publications: list[dict],
    profile: dict,
) -> list[Alert]:
    alerts: list[Alert] = []
    published_count = sum(1 for p in publications if p.get("status") == "published")

    if published_count == 0 and profile.get("orcid_id"):
        alerts.append(Alert(
            code="NO_PUBLICATIONS", level="info", category="publications",
            title="No publications on record",
            message="Import your publications from ORCID to build your impact profile.",
            action="Import publications", action_url="/profile/publications",
        ))

    # Stale drafts
    stale_drafts = [
        p for p in publications
        if p.get("status") in ("draft", "in_progress")
        and age_in_days(parse_date(p.get("updated_at") or p.get("created_at")) or
                        __import__("datetime").datetime.now()) > 90
    ]
    if stale_drafts:
        alerts.append(Alert(
            code="STALE_DRAFTS", level="info", category="publications",
            title=f"{len(stale_drafts)} stale manuscript(s)",
            message=f"You have {len(stale_drafts)} manuscript(s) not updated in 90+ days.",
            action="Review manuscripts", action_url="/manuscripts",
            data={"count": len(stale_drafts)},
        ))

    return alerts


def generate_grant_alerts(
    grant_applications: list[dict],
    deadline_warning_days: int = 14,
) -> list[Alert]:
    alerts: list[Alert] = []

    for app in grant_applications:
        deadline_str = app.get("deadline") or app.get("submission_deadline")
        if not deadline_str:
            continue
        dt = parse_date(deadline_str)
        if not dt:
            continue
        d = days_until(dt)
        if 0 <= d <= deadline_warning_days:
            level = "critical" if d <= 3 else "warning"
            alerts.append(Alert(
                code="GRANT_DEADLINE_APPROACHING", level=level, category="grants",
                title=f"Grant deadline in {d} day(s)",
                message=f"'{app.get('grant_title', 'Grant')}' deadline is {dt.strftime('%Y-%m-%d')}.",
                action="View application", action_url=f"/grant-hub/{app.get('_id', '')}",
                data={"days_remaining": d, "grant_id": str(app.get("_id", ""))},
            ))
        elif d < 0:
            if app.get("status") == "submitted":
                pass  # Already submitted — no alert
            else:
                alerts.append(Alert(
                    code="GRANT_DEADLINE_PASSED", level="info", category="grants",
                    title="Grant deadline passed",
                    message=f"The deadline for '{app.get('grant_title', 'Grant')}' has passed.",
                ))

    return alerts


def generate_account_alerts(
    account: dict,
    credits_low_threshold: int = 10,
    storage_high_threshold_pct: float = 90.0,
) -> list[Alert]:
    alerts: list[Alert] = []

    raw_credits = account.get("credits_balance") if account.get("credits_balance") is not None else account.get("ai_credits")
    credits = int(raw_credits) if raw_credits is not None else 999
    if credits < credits_low_threshold:
        level = "critical" if credits == 0 else "warning"
        alerts.append(Alert(
            code="LOW_AI_CREDITS", level=level, category="account",
            title="AI credits running low",
            message=f"You have {credits} AI credit(s) remaining.",
            action="Add credits", action_url="/billing",
            data={"credits_remaining": credits},
        ))

    storage_pct = float(account.get("storage_used_pct") or 0)
    if storage_pct >= storage_high_threshold_pct:
        alerts.append(Alert(
            code="STORAGE_NEAR_FULL", level="warning", category="account",
            title=f"Storage {storage_pct:.0f}% used",
            message="You are approaching your storage limit. Delete unused files or upgrade your plan.",
            action="Manage storage", action_url="/files",
            data={"storage_pct": storage_pct},
        ))

    # Subscription expiry
    sub_end = parse_date(account.get("subscription_end_date"))
    if sub_end:
        d = days_until(sub_end)
        if 0 <= d <= 14:
            alerts.append(Alert(
                code="SUBSCRIPTION_EXPIRING", level="warning", category="account",
                title=f"Subscription expires in {d} day(s)",
                message=f"Your subscription expires on {sub_end.strftime('%Y-%m-%d')}.",
                action="Renew subscription", action_url="/billing",
                data={"days_remaining": d},
            ))

    return alerts


def generate_activity_alerts(
    activity_stats: dict,
    inactivity_threshold_days: int = 30,
) -> list[Alert]:
    alerts: list[Alert] = []
    days_inactive = int(activity_stats.get("days_since_last_login") or 0)

    if days_inactive >= inactivity_threshold_days:
        alerts.append(Alert(
            code="USER_INACTIVE", level="info", category="activity",
            title=f"You've been inactive for {days_inactive} days",
            message="Return to complete your pending tasks and check new collaboration requests.",
            action="Go to dashboard", action_url="/dashboard",
        ))

    inactive_projects = int(activity_stats.get("inactive_projects") or 0)
    if inactive_projects > 0:
        alerts.append(Alert(
            code="INACTIVE_PROJECTS", level="info", category="activity",
            title=f"{inactive_projects} project(s) need attention",
            message="Some of your projects have had no activity in 30+ days.",
            action="Review projects", action_url="/projects",
        ))

    return alerts


def generate_all_alerts(
    profile: dict,
    publications: list[dict] | None = None,
    grant_applications: list[dict] | None = None,
    account: dict | None = None,
    activity_stats: dict | None = None,
) -> list[Alert]:
    """Aggregate all alert types in priority order."""
    alerts: list[Alert] = []

    alerts.extend(generate_profile_alerts(profile))
    if publications is not None:
        alerts.extend(generate_publication_alerts(publications, profile))
    if grant_applications is not None:
        alerts.extend(generate_grant_alerts(grant_applications))
    if account is not None:
        alerts.extend(generate_account_alerts(account))
    if activity_stats is not None:
        alerts.extend(generate_activity_alerts(activity_stats))

    level_order = {"critical": 0, "warning": 1, "info": 2}
    return sorted(alerts, key=lambda a: level_order.get(a.level, 3))
