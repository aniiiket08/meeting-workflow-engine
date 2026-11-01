import hashlib
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import logging

from app.db.models.action import ActionItem, ActionStatus
from app.db.models.minutes import Minutes, MinutesStatus
from app.core.errors import ToolError
from app.services.email_service import email_service, SentReminder, ReminderLevel
from app.observability.tracer import record_tool_call, trace_agent

logger = logging.getLogger("meeting_organizer")

@trace_agent(agent_name="reminder_agent")
def run_reminder_agent(
    db: Session,
    meeting_id: int | None = None,
    now: datetime | None = None,
) -> Dict[str, Any]:
    """
    Reminder Agent & Escalation Ladder:
    1. Level 1 (Gentle): 2 days before due date.
    2. Level 2 (Nudge): Due date or 1 day past due.
    3. Level 3 (Escalate to Chair): >2 days overdue.
    Uses idempotency keys so retries never send duplicate emails.
    """
    now = now or datetime.now(timezone.utc)
    approved_meetings = db.query(Minutes.meeting_id).filter(Minutes.status == MinutesStatus.APPROVED)
    query = db.query(ActionItem).filter(
        ActionItem.status != ActionStatus.COMPLETED,
        ActionItem.meeting_id.in_(approved_meetings),
    )
    if meeting_id is not None:
        query = query.filter(ActionItem.meeting_id == meeting_id)
    open_items = query.all()
    record_tool_call(
        "database.open_action_items",
        {"meeting_id": meeting_id},
        {"count": len(open_items)},
    )

    sent_count = 0
    for item in open_items:
        if not item.due_date or not item.owner:
            continue

        due_dt = item.due_date
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=timezone.utc)
        days_diff = (due_dt.date() - now.date()).days

        target_level = None
        if days_diff == 2:
            target_level = ReminderLevel.GENTLE
        elif days_diff <= 0 and days_diff >= -1:
            target_level = ReminderLevel.NUDGE
        elif days_diff < -1:
            target_level = ReminderLevel.ESCALATE_CHAIR

        if not target_level:
            continue

        idempotency_key = hashlib.sha256(f"{item.id}_{target_level.value}_{item.due_date.strftime('%Y%m%d')}".encode("utf-8")).hexdigest()

        existing = db.query(SentReminder).filter(SentReminder.idempotency_key == idempotency_key).first()
        if existing:
            if existing.status != "sent":
                raise ToolError(
                    "A previous reminder email attempt has an uncertain outcome; reconcile delivery before retrying.",
                    tool_name="email_service.send_email",
                )
            continue

        subject = f"[{target_level.value.upper()}] Action Item Reminder: {item.description}"
        body = f"Hello {item.owner.name},\n\nReminder for your action item: '{item.description}' due on {item.due_date.strftime('%Y-%m-%d')}."

        to_email = item.owner.email
        reminder_rec = SentReminder(
            action_item_id=item.id,
            level=target_level,
            sent_to_email=to_email,
            idempotency_key=idempotency_key,
            status="sending",
        )
        db.add(reminder_rec)
        db.commit()
        try:
            sent = email_service.send_email(
                to_email=to_email,
                subject=subject,
                body=body,
                idempotency_key=idempotency_key,
            )
        except ToolError:
            reminder_rec.status = "uncertain"
            db.commit()
            raise
        except Exception as exc:
            logger.exception("Reminder delivery failed for action_id=%s", item.id)
            reminder_rec.status = "uncertain"
            db.commit()
            raise ToolError(
                "Could not deliver an action reminder.",
                tool_name="email_service.send_email",
            ) from exc
        if not sent:
            logger.error("Reminder delivery returned false for action_id=%s", item.id)
            reminder_rec.status = "uncertain"
            db.commit()
            raise ToolError(
                "Could not deliver an action reminder.",
                tool_name="email_service.send_email",
            )
        record_tool_call(
            "email_service.send_email",
            {"action_id": item.id, "reminder_level": target_level.value},
            {"sent": True},
        )

        reminder_rec.status = "sent"
        db.commit()
        sent_count += 1

    return {"reminders_sent": sent_count}
