import hashlib
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.core.errors import ApprovalRequired, NotFound, ToolError, ValidationFailed
from app.core.logging import setup_logging
from app.db.models.minutes import Minutes, MinutesStatus
from app.db.models.meeting import Meeting, Attendee
from app.db.models.audit import AuditLog
from app.services.email_service import email_service
from app.observability.tracer import record_tool_call, trace_agent

logger = setup_logging()

@trace_agent(agent_name="distribution_agent")
def run_distribution_agent(db: Session, meeting_id: int) -> Dict[str, Any]:
    """
    Distribution Agent:
    Distributes approved minutes PDF & iCal to all meeting attendees with audit logging.
    """
    minutes = db.query(Minutes).filter(Minutes.meeting_id == meeting_id, Minutes.status == MinutesStatus.APPROVED).first()
    if not minutes:
        raise ApprovalRequired("Minutes must be approved before distribution.")

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise NotFound(entity="Meeting", identifier=meeting_id)
    attendees = db.query(Attendee).filter(Attendee.meeting_id == meeting_id).all()
    recipients = [att.user.email for att in attendees if att.user]
    if not recipients:
        raise ValidationFailed("Approved minutes cannot be distributed without attendees.")

    pdf_bytes = None
    pdf_status = "attached"
    try:
        pdf_bytes = email_service.generate_pdf_minutes(minutes.summary, minutes.key_discussion_points)
        record_tool_call("email_service.generate_pdf_minutes", {"meeting_id": meeting_id}, {"bytes": len(pdf_bytes)})
    except ToolError as exc:
        logger.warning("PDF generation failed for meeting_id=%s: %s. Proceeding without PDF attachment.", meeting_id, exc)
        pdf_status = "PDF unavailable"
        record_tool_call("email_service.generate_pdf_minutes", {"meeting_id": meeting_id}, {"error": str(exc), "status": "unavailable"})
    except Exception as exc:
        logger.warning("Unexpected error during PDF generation for meeting_id=%s: %s. Proceeding without PDF attachment.", meeting_id, exc)
        pdf_status = "PDF unavailable"
        record_tool_call("email_service.generate_pdf_minutes", {"meeting_id": meeting_id}, {"error": str(exc), "status": "unavailable"})

    ics_text = email_service.generate_ics_calendar(
        title=meeting.title,
        start_iso=meeting.start_time.isoformat() if meeting.start_time else "",
        end_iso=meeting.end_time.isoformat() if meeting.end_time else "",
    )
    record_tool_call("email_service.generate_ics_calendar", {"meeting_id": meeting_id}, {"characters": len(ics_text)})

    existing_logs = db.query(AuditLog).filter(
        AuditLog.action == "DISTRIBUTE_MINUTES",
        AuditLog.entity == "Meeting",
    ).all()
    for log in existing_logs:
        details = log.details or {}
        if details.get("meeting_id") == meeting_id and details.get("content_hash") == minutes.content_hash:
            return {
                "status": "already_distributed",
                "recipients": details.get("recipients", []),
                "pdf_status": details.get("pdf_status", pdf_status),
            }

    distributed_emails = []
    attachments: list[tuple[str, bytes, str]] = []
    if pdf_bytes:
        attachments.append(("minutes.pdf", pdf_bytes, "application/pdf"))
    attachments.append(("meeting.ics", ics_text.encode("utf-8"), "text/calendar"))

    for att in attendees:
        if not att.user:
            continue
        recipient = att.user.email
        idempotency_key = hashlib.sha256(
            f"dist_{meeting_id}_{recipient}_{minutes.content_hash}".encode("utf-8")
        ).hexdigest()
        attempt = next(
            (
                log
                for log in db.query(AuditLog)
                .filter(AuditLog.action == "DISTRIBUTE_MINUTES_ATTEMPT")
                .all()
                if (log.details or {}).get("idempotency_key") == idempotency_key
            ),
            None,
        )
        if attempt:
            attempt_status = (attempt.details or {}).get("status")
            if attempt_status == "sent":
                distributed_emails.append(recipient)
                continue
            raise ToolError(
                "A previous SMTP attempt has an uncertain outcome; reconcile delivery before retrying.",
                tool_name="email_service.send_email",
            )
        delivered = db.query(AuditLog).filter(
            AuditLog.action == "DISTRIBUTE_MINUTES_RECIPIENT"
        ).all()
        if any((log.details or {}).get("idempotency_key") == idempotency_key for log in delivered):
            distributed_emails.append(recipient)
            continue

        attempt = AuditLog(
            actor="system",
            action="DISTRIBUTE_MINUTES_ATTEMPT",
            entity="Meeting",
            details={
                "meeting_id": meeting_id,
                "recipient": recipient,
                "content_hash": minutes.content_hash,
                "idempotency_key": idempotency_key,
                "status": "sending",
                "pdf_status": pdf_status,
            },
        )
        db.add(attempt)
        db.commit()
        try:
            sent = email_service.send_email(
                to_email=recipient,
                subject=f"Approved Minutes: {meeting.title}",
                body=f"Please find the approved meeting minutes attached.\n\nSummary:\n{minutes.summary}",
                idempotency_key=idempotency_key,
                attachments=attachments,
            )
        except ToolError as exc:
            attempt.details = {**(attempt.details or {}), "status": "uncertain", "error": str(exc)}
            db.commit()
            raise
        except Exception as exc:
            logger.exception("Approved minutes delivery failed for meeting_id=%s", meeting_id)
            attempt.details = {**(attempt.details or {}), "status": "uncertain"}
            db.commit()
            raise ToolError("Could not deliver approved minutes.", tool_name="email_service.send_email") from exc
        if not sent:
            logger.error("Minutes delivery returned false for meeting_id=%s", meeting_id)
            attempt.details = {**(attempt.details or {}), "status": "uncertain"}
            db.commit()
            raise ToolError("Could not deliver approved minutes.", tool_name="email_service.send_email")
        attempt.details = {**(attempt.details or {}), "status": "sent"}
        record_tool_call(
            "email_service.send_email",
            {"meeting_id": meeting_id, "recipient": recipient},
            {"sent": True},
        )
        db.add(
            AuditLog(
                actor="system",
                action="DISTRIBUTE_MINUTES_RECIPIENT",
                entity="Meeting",
                details={
                    "meeting_id": meeting_id,
                    "recipient": recipient,
                    "content_hash": minutes.content_hash,
                    "idempotency_key": idempotency_key,
                    "pdf_status": pdf_status,
                },
            )
        )
        db.commit()
        distributed_emails.append(recipient)

    audit_entry = AuditLog(
        actor="system",
        action="DISTRIBUTE_MINUTES",
        entity="Meeting",
        details={
            "meeting_id": meeting_id,
            "recipients": distributed_emails,
            "content_hash": minutes.content_hash,
            "pdf_status": pdf_status,
        },
    )
    db.add(audit_entry)
    db.commit()

    return {
        "status": "distributed",
        "recipients": distributed_emails,
        "pdf_bytes_size": len(pdf_bytes) if pdf_bytes else 0,
        "pdf_status": pdf_status,
    }
