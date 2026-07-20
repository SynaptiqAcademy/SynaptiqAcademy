"""Unified Notification Engine — merge all platform notification streams."""
from __future__ import annotations

import threading
import time
from collections import defaultdict

from .models import Notification, NotificationPriority, NotificationType

_MAX_PER_COHORT = 500
_PRIORITY_ORDER = {
    NotificationPriority.CRITICAL.value: 0,
    NotificationPriority.HIGH.value:     1,
    NotificationPriority.NORMAL.value:   2,
    NotificationPriority.LOW.value:      3,
}

_TYPE_PRIORITY: dict[str, str] = {
    NotificationType.GRANT_DEADLINE.value:       NotificationPriority.HIGH.value,
    NotificationType.CONFERENCE_DEADLINE.value:  NotificationPriority.HIGH.value,
    NotificationType.REVIEW_COMPLETE.value:      NotificationPriority.NORMAL.value,
    NotificationType.AI_INSIGHT.value:           NotificationPriority.LOW.value,
    NotificationType.COLLABORATION_REQUEST.value: NotificationPriority.HIGH.value,
    NotificationType.CITATION_ALERT.value:       NotificationPriority.NORMAL.value,
    NotificationType.CAREER_ALERT.value:         NotificationPriority.NORMAL.value,
    NotificationType.INSTITUTION_ALERT.value:    NotificationPriority.NORMAL.value,
    NotificationType.WORKFLOW_COMPLETE.value:    NotificationPriority.NORMAL.value,
    NotificationType.AUTOMATION_TRIGGERED.value: NotificationPriority.NORMAL.value,
    NotificationType.SYSTEM_ALERT.value:         NotificationPriority.CRITICAL.value,
    NotificationType.JOURNAL_RECOMMENDATION.value: NotificationPriority.LOW.value,
    NotificationType.PUBLICATION_ALERT.value:   NotificationPriority.NORMAL.value,
}


class NotificationEngine:
    def __init__(self):
        self._lock  = threading.Lock()
        # cohort → list[Notification]
        self._inbox: dict[str, list[Notification]] = defaultdict(list)

    def notify(
        self,
        notification_type: str,
        user_cohort:       str,
        title:             str,
        body:              str  = "",
        priority:          str | None = None,
        action_url:        str  = "",
        expires_at:        float = 0.0,
        metadata:          dict | None = None,
    ) -> Notification:
        resolved_priority = priority or _TYPE_PRIORITY.get(notification_type, NotificationPriority.NORMAL.value)
        notif = Notification(
            notification_type=notification_type,
            priority=resolved_priority,
            title=title,
            body=body,
            action_url=action_url,
            user_cohort=user_cohort,
            expires_at=expires_at,
            metadata=metadata or {},
        )
        with self._lock:
            inbox = self._inbox[user_cohort]
            inbox.append(notif)
            if len(inbox) > _MAX_PER_COHORT:
                # evict oldest read notifications first, then oldest unread
                reads   = [n for n in inbox if n.read]
                unreads = [n for n in inbox if not n.read]
                if reads:
                    reads.pop(0)
                else:
                    unreads.pop(0)
                self._inbox[user_cohort] = unreads + reads
        return notif

    def get_notifications(
        self,
        user_cohort: str,
        unread_only: bool = False,
        limit:       int  = 50,
        priority:    str | None = None,
    ) -> list[Notification]:
        now = time.time()
        with self._lock:
            notifs = list(self._inbox.get(user_cohort, []))
        # Expire
        notifs = [n for n in notifs if n.expires_at == 0 or n.expires_at > now]
        if unread_only:
            notifs = [n for n in notifs if not n.read]
        if priority:
            notifs = [n for n in notifs if n.priority == priority]
        notifs.sort(key=lambda n: (_PRIORITY_ORDER.get(n.priority, 99), -n.created_at))
        return notifs[:limit]

    def mark_read(self, notification_id: str, user_cohort: str) -> bool:
        with self._lock:
            for n in self._inbox.get(user_cohort, []):
                if n.notification_id == notification_id:
                    n.read = True
                    return True
        return False

    def mark_all_read(self, user_cohort: str) -> int:
        with self._lock:
            count = 0
            for n in self._inbox.get(user_cohort, []):
                if not n.read:
                    n.read = True
                    count += 1
        return count

    def dismiss(self, notification_id: str, user_cohort: str) -> bool:
        with self._lock:
            inbox = self._inbox.get(user_cohort, [])
            for i, n in enumerate(inbox):
                if n.notification_id == notification_id:
                    inbox.pop(i)
                    return True
        return False

    def get_unread_count(self, user_cohort: str) -> int:
        now = time.time()
        with self._lock:
            notifs = self._inbox.get(user_cohort, [])
        return sum(
            1 for n in notifs
            if not n.read and (n.expires_at == 0 or n.expires_at > now)
        )

    def broadcast(
        self,
        notification_type: str,
        cohorts:           list[str],
        title:             str,
        body:              str = "",
    ) -> list[Notification]:
        return [self.notify(notification_type, c, title, body) for c in cohorts]

    def stats(self) -> dict:
        with self._lock:
            total   = sum(len(v) for v in self._inbox.values())
            unread  = sum(1 for v in self._inbox.values() for n in v if not n.read)
            cohorts = len(self._inbox)
        return {"total": total, "unread": unread, "cohorts": cohorts}
