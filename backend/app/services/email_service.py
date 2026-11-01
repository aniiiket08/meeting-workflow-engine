from datetime import datetime, timezone
import logging
import smtplib
from email.message import EmailMessage
from html import escape
from typing import List, Dict, Any
from sqlalchemy import DateTime, Enum as PyEnum, ForeignKey, String, Text, Integer, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from app.db.base import Base
from app.config import settings
from app.core.errors import ToolError, ValidationFailed

logger = logging.getLogger("meeting_organizer")

class ReminderLevel(str, enum.Enum):
    GENTLE = "gentle"
    NUDGE = "nudge"
    ESCALATE_CHAIR = "escalate_chair"

class SentReminder(Base):
    __tablename__ = "sent_reminders"

    action_item_id: Mapped[int] = mapped_column(ForeignKey("action_items.id"), nullable=False)
    level: Mapped[ReminderLevel] = mapped_column(
        PyEnum(ReminderLevel, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    sent_to_email: Mapped[str] = mapped_column(String(255), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="sent", nullable=False)

    action_item = relationship("ActionItem")


class EmailService:
    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        idempotency_key: str,
        attachments: list[tuple[str, bytes, str]] | None = None,
    ) -> bool:
        """Send a real SMTP message; never claim delivery when SMTP is unconfigured."""
        if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
            logger.error("SMTP delivery requested but no SMTP host/from address is configured")
            raise ToolError(
                "Email delivery is not configured. Set SMTP_HOST and SMTP_FROM_EMAIL.",
                tool_name="smtp.send_email",
            )

        message = EmailMessage()
        message["From"] = settings.SMTP_FROM_EMAIL
        message["To"] = to_email
        message["Subject"] = subject
        message["X-Idempotency-Key"] = idempotency_key
        message.set_content(body)
        for filename, content, mime_type in attachments or []:
            maintype, _, subtype = mime_type.partition("/")
            if not maintype or not subtype:
                raise ValidationFailed(f"Invalid attachment content type: {mime_type!r}.")
            message.add_attachment(
                content,
                maintype=maintype,
                subtype=subtype,
                filename=filename,
            )

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=20) as server:
                if settings.SMTP_STARTTLS:
                    server.starttls()
                if settings.SMTP_USERNAME:
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD or "")
                server.send_message(message)
            return True
        except Exception as exc:
            logger.exception("SMTP delivery failed")
            raise ToolError("Email delivery failed.", tool_name="smtp.send_email") from exc

    def generate_pdf_minutes(self, summary: str, points: List[str]) -> bytes:
        """Render approved minutes to a real PDF document.
        
        Raises ToolError when PDF generation libraries are unavailable or rendering fails.
        Never generates placeholder or fake PDF bytes.
        """
        point_markup = "".join(f"<li>{escape(point)}</li>" for point in points)
        document = (
            "<h1>Meeting Minutes</h1><h2>Summary</h2>"
            f"<p>{escape(summary)}</p><h2>Key discussion points</h2><ul>{point_markup}</ul>"
        )
        try:
            from weasyprint import HTML
            return HTML(string=document).write_pdf()
        except Exception as exc:
            logger.warning("WeasyPrint rendering unavailable: %s", exc)
            raise ToolError(
                f"WeasyPrint rendering unavailable: {exc}",
                tool_name="pdf.render",
            ) from exc

    def generate_ics_calendar(self, title: str, start_iso: str, end_iso: str) -> str:
        """Generate iCalendar event data with escaped text and UTC timestamps."""
        if not start_iso or not end_iso:
            raise ValidationFailed("Meeting start and end times are required to generate an invite.")
        safe_title = title.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

        def to_ics_time(value: str) -> str:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

        return f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
SUMMARY:{safe_title}
DTSTART:{to_ics_time(start_iso)}
DTEND:{to_ics_time(end_iso)}
END:VEVENT
END:VCALENDAR"""

email_service = EmailService()
