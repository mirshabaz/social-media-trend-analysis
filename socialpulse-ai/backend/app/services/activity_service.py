import json
from typing import Any

from sqlalchemy.orm import Session

from app.models.system import ActivityRecord, NotificationRecord


def record_event(
    db: Session,
    *,
    action: str,
    title: str,
    message: str,
    category: str = "dataset",
    severity: str = "info",
    target_type: str = "dataset",
    target_name: str = "",
    user_id: int | None = None,
    meta: dict[str, Any] | None = None,
    commit: bool = True,
) -> tuple[ActivityRecord, NotificationRecord]:
    activity = ActivityRecord(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_name=target_name,
        details=message,
    )
    notification = NotificationRecord(
        user_id=user_id,
        title=title,
        message=message,
        category=category,
        severity=severity,
        is_read=False,
        meta_json=json.dumps(meta or {}),
    )
    db.add(activity)
    db.add(notification)
    if commit:
        db.commit()
    return activity, notification

