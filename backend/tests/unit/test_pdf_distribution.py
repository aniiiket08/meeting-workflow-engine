import hashlib
import sys
import types
from datetime import datetime, timezone
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.errors import ToolError
from app.db.base import Base
from app.services.email_service import email_service
from app.config import settings
from app.agents.distribution import run_distribution_agent
from app.db.models.minutes import Minutes, MinutesStatus
from app.db.models.meeting import Meeting, Attendee
from app.db.models.user import User, UserRole
from app.db.models.audit import AuditLog
import app.observability.tracer as tracer_module

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def db():
    original_tracer_session = tracer_module.SessionLocal
    tracer_module.SessionLocal = TestingSessionLocal
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        tracer_module.SessionLocal = original_tracer_session


def test_pdf_generation_success():
    mock_weasyprint = types.ModuleType("weasyprint")
    mock_html_cls = MagicMock()
    mock_instance = MagicMock()
    mock_instance.write_pdf.return_value = b"%PDF-1.4 real pdf bytes"
    mock_html_cls.return_value = mock_instance
    mock_weasyprint.HTML = mock_html_cls

    with patch.dict("sys.modules", {"weasyprint": mock_weasyprint}):
        pdf_bytes = email_service.generate_pdf_minutes("Summary text", ["Point 1", "Point 2"])
        assert pdf_bytes == b"%PDF-1.4 real pdf bytes"
        mock_instance.write_pdf.assert_called_once()


def test_pdf_generation_unavailable_raises_tool_error():
    with patch.dict("sys.modules", {"weasyprint": None}):
        with pytest.raises(ToolError) as exc_info:
            email_service.generate_pdf_minutes("Summary text", ["Point 1"])
        assert exc_info.value.details.get("tool") == "pdf.render"
        assert "WeasyPrint rendering unavailable" in str(exc_info.value)


def test_distribution_agent_succeeds_when_pdf_fails(db, monkeypatch):
    user = User(
        name="Test Attendee",
        username="attendee",
        email="attendee@example.com",
        role=UserRole.STUDENT,
        hashed_password="pw",
    )
    db.add(user)
    db.flush()

    meeting = Meeting(
        title="Status Sync",
        start_time=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 1, 10, 30, tzinfo=timezone.utc),
        organizer_id=user.id,
        status="scheduled",
    )
    db.add(meeting)
    db.flush()

    attendee = Attendee(meeting_id=meeting.id, user_id=user.id)
    db.add(attendee)

    minutes = Minutes(
        meeting_id=meeting.id,
        summary="Sprint progress",
        key_discussion_points=["Item 1", "Item 2"],
        status=MinutesStatus.APPROVED,
        content_hash="testhash12345",
    )
    db.add(minutes)
    db.commit()

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.invalid")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "sender@test.invalid")
    with patch.object(email_service, "generate_pdf_minutes", side_effect=ToolError("No GTK", tool_name="pdf.render")):
        with patch.object(email_service, "send_email", return_value=True) as mock_send:
            res = run_distribution_agent(db, meeting.id)
            assert res["status"] == "distributed"
            assert res["pdf_status"] == "PDF unavailable"
            assert res["pdf_bytes_size"] == 0
            assert "attendee@example.com" in res["recipients"]

            # Verify send_email was called with only .ics attachment (no fake PDF)
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]
            attachments = call_kwargs["attachments"]
            filenames = [a[0] for a in attachments]
            assert "minutes.pdf" not in filenames
            assert "meeting.ics" in filenames


def test_distribution_does_not_repeat_an_ambiguous_smtp_attempt(db, monkeypatch):
    user = User(
        name="Retry Attendee",
        username="retry-attendee",
        email="retry@example.com",
        role=UserRole.STUDENT,
        hashed_password="pw",
    )
    db.add(user)
    db.flush()
    meeting = Meeting(
        title="Retry Safety",
        start_time=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 1, 10, 30, tzinfo=timezone.utc),
        organizer_id=user.id,
        status="scheduled",
    )
    db.add(meeting)
    db.flush()
    db.add(Attendee(meeting_id=meeting.id, user_id=user.id))
    db.add(
        Minutes(
            meeting_id=meeting.id,
            summary="Approved summary",
            key_discussion_points=[],
            status=MinutesStatus.APPROVED,
            content_hash="ambiguous-delivery-test",
        )
    )
    db.commit()

    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.invalid")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "sender@test.invalid")
    with patch.object(email_service, "generate_pdf_minutes", return_value=b"pdf"):
        with patch.object(email_service, "send_email", side_effect=ToolError("connection lost")) as send:
            with pytest.raises(ToolError, match="connection lost"):
                run_distribution_agent(db, meeting.id)
            with pytest.raises(ToolError, match="uncertain outcome"):
                run_distribution_agent(db, meeting.id)
            assert send.call_count == 1
            attempt = (
                db.query(AuditLog)
                .filter(AuditLog.action == "DISTRIBUTE_MINUTES_ATTEMPT")
                .one()
            )
            assert attempt.details["status"] == "uncertain"


def test_distribution_missing_smtp_is_reported_before_any_send_attempt(db, monkeypatch):
    user = User(
        name="Not Configured Attendee",
        username="not-configured-attendee",
        email="not-configured@example.com",
        role=UserRole.STUDENT,
        hashed_password="pw",
    )
    db.add(user)
    db.flush()
    meeting = Meeting(
        title="SMTP Preflight",
        organizer_id=user.id,
        status="scheduled",
    )
    db.add(meeting)
    db.flush()
    db.add(Attendee(meeting_id=meeting.id, user_id=user.id))
    db.add(
        Minutes(
            meeting_id=meeting.id,
            summary="Approved summary",
            key_discussion_points=[],
            status=MinutesStatus.APPROVED,
            content_hash="smtp-preflight-test",
        )
    )
    db.commit()
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", None)

    with pytest.raises(ToolError, match="Email delivery is not configured"):
        run_distribution_agent(db, meeting.id)

    attempts = db.query(AuditLog).filter(
        AuditLog.action == "DISTRIBUTE_MINUTES_ATTEMPT"
    ).all()
    assert not any((attempt.details or {}).get("meeting_id") == meeting.id for attempt in attempts)


def test_legacy_not_configured_attempt_can_be_retried_after_smtp_setup(db, monkeypatch):
    user = User(
        name="Recovered Attendee",
        username="recovered-attendee",
        email="recovered@example.com",
        role=UserRole.STUDENT,
        hashed_password="pw",
    )
    db.add(user)
    db.flush()
    meeting = Meeting(
        title="Recover SMTP Attempt",
        start_time=datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 1, 10, 30, tzinfo=timezone.utc),
        organizer_id=user.id,
        status="scheduled",
    )
    db.add(meeting)
    db.flush()
    db.add(Attendee(meeting_id=meeting.id, user_id=user.id))
    minutes = Minutes(
        meeting_id=meeting.id,
        summary="Approved summary",
        key_discussion_points=[],
        status=MinutesStatus.APPROVED,
        content_hash="legacy-not-configured-attempt",
    )
    db.add(minutes)
    db.flush()
    idempotency_key = hashlib.sha256(
        f"dist_{meeting.id}_{user.email}_{minutes.content_hash}".encode("utf-8")
    ).hexdigest()
    attempt = AuditLog(
        actor="system",
        action="DISTRIBUTE_MINUTES_ATTEMPT",
        entity="Meeting",
        details={
            "meeting_id": meeting.id,
            "recipient": user.email,
            "content_hash": minutes.content_hash,
            "idempotency_key": idempotency_key,
            "status": "uncertain",
            "error": "Email delivery is not configured. Set SMTP_HOST and SMTP_FROM_EMAIL.",
        },
    )
    db.add(attempt)
    db.commit()
    monkeypatch.setattr(settings, "SMTP_HOST", "smtp.test.invalid")
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", "sender@test.invalid")

    with patch.object(email_service, "generate_pdf_minutes", return_value=b"pdf"):
        with patch.object(email_service, "send_email", return_value=True) as send:
            result = run_distribution_agent(db, meeting.id)

    assert result["status"] == "distributed"
    send.assert_called_once()
    db.refresh(attempt)
    assert attempt.details["status"] == "sent"
