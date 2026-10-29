"""Tests for Issue 6 (reminders/email), Issue 7 (Whisper STT), Issue 8 (frontend/backend errors).

These regression tests cover:
- Reminder idempotency, escalation levels, overdue items
- Email configuration errors vs false success
- Whisper model caching, unsupported formats, empty audio, mocked transcription
- API error shapes (structured AppError, validation list detail, plain string detail)
- ActionAssignRequest accepting both user_id and owner_id fields
"""
import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.models
import app.observability.tracer as tracer_module
from app.core.errors import ToolError, ValidationFailed
from app.db.base import Base
from app.db.models.action import ActionItem, ActionPriority, ActionStatus
from app.db.models.meeting import Attendee, Meeting, MeetingStatus
from app.db.models.minutes import Minutes, MinutesStatus
from app.db.models.room import Room
from app.db.models.user import User, UserRole
from app.services.email_service import SentReminder, email_service
from app.agents.reminder import run_reminder_agent
from app.services.stt import STTService, _SUPPORTED_EXTENSIONS


@pytest.fixture
def test_db(monkeypatch):
    """In-memory SQLite database for isolated testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session_local = sessionmaker(autoflush=False, bind=engine)
    monkeypatch.setattr(tracer_module, "SessionLocal", test_session_local)

    db = test_session_local()
    admin = User(
        name="Chairman",
        username="test-chair",
        email="chair@test.local",
        role=UserRole.CHAIRMAN,
        hashed_password="unused",
    )
    teacher = User(
        name="Teacher",
        username="test-teacher",
        email="teacher@test.local",
        role=UserRole.TEACHER,
        hashed_password="unused",
    )
    room = Room(name="Test Room", capacity=10, equipment=["projector"])
    db.add_all([admin, teacher, room])
    db.commit()
    meeting = Meeting(
        title="Test Meeting",
        description="Covers regression tests",
        duration_minutes=60,
        organizer_id=admin.id,
        status=MeetingStatus.ROOM_BOOKED,
        room_id=room.id,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    db.add(Attendee(meeting_id=meeting.id, user_id=teacher.id))
    db.commit()
    yield db, meeting, admin, teacher, room
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ── Issue 6: Reminder idempotency and escalation ────────────────────────────

def test_reminder_idempotency_prevents_duplicate_sends(test_db, monkeypatch):
    """Running the reminder agent twice for the same action should not send duplicates."""
    db, meeting, admin, _, _ = test_db
    db.add(
        Minutes(
            meeting_id=meeting.id,
            version=1,
            summary="Approved",
            key_discussion_points=[],
            action_items_json=[],
            status=MinutesStatus.APPROVED,
            content_hash="idem-approved",
            approved_by_id=admin.id,
        )
    )
    now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    db.add(
        ActionItem(
            meeting_id=meeting.id,
            description="Overdue task",
            owner_id=admin.id,
            due_date=now - timedelta(days=3),
            priority=ActionPriority.HIGH,
            status=ActionStatus.PENDING,
            source_quote="source",
            confidence=1.0,
        )
    )
    db.commit()

    sends = []
    monkeypatch.setattr(
        email_service, "send_email",
        lambda *args, **kwargs: sends.append(kwargs.get("subject", args[1] if len(args) > 1 else "")) or True,
    )

    first = run_reminder_agent(db, meeting.id, now=now)
    second = run_reminder_agent(db, meeting.id, now=now)
    assert first["reminders_sent"] == 1
    assert second["reminders_sent"] == 0
    assert len(sends) == 1


def test_reminder_escalation_levels(test_db, monkeypatch):
    """Verify that gentle, nudge, and escalate_chair levels trigger at correct intervals."""
    db, meeting, admin, _, _ = test_db
    db.add(
        Minutes(
            meeting_id=meeting.id,
            version=1,
            summary="Approved",
            key_discussion_points=[],
            action_items_json=[],
            status=MinutesStatus.APPROVED,
            content_hash="escalation-approved",
            approved_by_id=admin.id,
        )
    )
    now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    # gentle: due_date exactly 2 days from now
    # nudge: due_date = now (0 days)
    # escalate: due_date = 2 days ago (-2 days)
    for desc, offset in (("gentle-task", 2), ("nudge-task", 0), ("escalate-task", -2)):
        db.add(
            ActionItem(
                meeting_id=meeting.id,
                description=desc,
                owner_id=admin.id,
                due_date=now + timedelta(days=offset),
                priority=ActionPriority.MEDIUM,
                status=ActionStatus.PENDING,
                source_quote="src",
                confidence=1.0,
            )
        )
    db.commit()

    subjects = []
    monkeypatch.setattr(
        email_service, "send_email",
        lambda *args, **kwargs: subjects.append(kwargs.get("subject", args[1] if len(args) > 1 else "")) or True,
    )

    result = run_reminder_agent(db, meeting.id, now=now)
    assert result["reminders_sent"] == 3
    levels = {r.level.value for r in db.query(SentReminder).all()}
    assert levels == {"gentle", "nudge", "escalate_chair"}


def test_email_unconfigured_raises_tool_error(test_db, monkeypatch):
    """Missing SMTP config should raise a ToolError, not silently succeed."""
    from app.config import settings
    monkeypatch.setattr(settings, "SMTP_HOST", None)
    monkeypatch.setattr(settings, "SMTP_FROM_EMAIL", None)

    with pytest.raises(ToolError, match="Email delivery is not configured"):
        email_service.send_email(
            to_email="test@example.com",
            subject="Test",
            body="Test body",
            idempotency_key="test-key-123",
        )


def test_reminder_skips_completed_items(test_db, monkeypatch):
    """Completed actions should not trigger reminders."""
    db, meeting, admin, _, _ = test_db
    db.add(
        Minutes(
            meeting_id=meeting.id,
            version=1,
            summary="Approved",
            key_discussion_points=[],
            action_items_json=[],
            status=MinutesStatus.APPROVED,
            content_hash="completed-approved",
            approved_by_id=admin.id,
        )
    )
    now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    db.add(
        ActionItem(
            meeting_id=meeting.id,
            description="Done task",
            owner_id=admin.id,
            due_date=now,
            priority=ActionPriority.HIGH,
            status=ActionStatus.COMPLETED,
            source_quote="src",
            confidence=1.0,
        )
    )
    db.commit()
    monkeypatch.setattr(
        email_service, "send_email",
        lambda *args, **kwargs: pytest.fail("Should not send for completed items"),
    )
    result = run_reminder_agent(db, meeting.id, now=now)
    assert result["reminders_sent"] == 0


# ── Issue 7: Whisper transcription ──────────────────────────────────────────

def test_stt_rejects_empty_audio():
    """Empty audio bytes should be rejected with a clear ValidationFailed."""
    stt = STTService()
    with pytest.raises(ValidationFailed, match="empty"):
        stt.transcribe(b"", "test.wav")


def test_stt_rejects_unsupported_format():
    """Unsupported file extensions should raise ValidationFailed with supported list."""
    stt = STTService()
    with pytest.raises(ValidationFailed, match="Unsupported audio format"):
        stt.transcribe(b"data", "document.pdf")


def test_stt_accepts_supported_formats():
    """Verify the supported extension set includes common audio formats."""
    assert ".wav" in _SUPPORTED_EXTENSIONS
    assert ".mp3" in _SUPPORTED_EXTENSIONS
    assert ".m4a" in _SUPPORTED_EXTENSIONS
    assert ".ogg" in _SUPPORTED_EXTENSIONS
    assert ".flac" in _SUPPORTED_EXTENSIONS


def test_stt_with_mocked_whisper_segments(monkeypatch):
    """Mocked Whisper model produces correct timestamped lines."""
    module = ModuleType("faster_whisper")

    class FakeWhisperModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, path, beam_size):
            assert Path(path).exists()
            return [
                SimpleNamespace(start=0.0, text=" Welcome everyone. "),
                SimpleNamespace(start=65.5, text=" Let's discuss the budget. "),
            ], SimpleNamespace(language="en")

    module.WhisperModel = FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", module)

    # Clear the cached model so the mock is used
    import app.services.stt as stt_mod
    monkeypatch.setattr(stt_mod, "_cached_model", None)

    stt = STTService()
    result = stt.transcribe(b"fake audio data", "meeting.wav")
    assert "[00:00:00] Welcome everyone." in result["text"]
    assert "[00:01:05] Let's discuss the budget." in result["text"]
    assert result["language"] == "en"
    assert result["hash"]  # SHA-256 hash is present


def test_stt_missing_whisper_raises_tool_error(monkeypatch):
    """When faster_whisper is not importable, a clear ToolError is raised."""
    monkeypatch.setitem(sys.modules, "faster_whisper", None)

    import app.services.stt as stt_mod
    monkeypatch.setattr(stt_mod, "_cached_model", None)

    stt = STTService()
    with pytest.raises(ToolError, match="transcription"):
        stt.transcribe(b"audio bytes", "meeting.wav")


def test_stt_pasted_transcript_fallback():
    """Manual transcript entry works as a fallback."""
    stt = STTService()
    result = stt.process_pasted_transcript("[00:00:01] Alice: Hello everyone.")
    assert result["text"] == "[00:00:01] Alice: Hello everyone."
    assert result["language"] == "en"
    assert result["hash"]


def test_stt_pasted_empty_text_rejected():
    """Empty pasted transcript should be rejected."""
    stt = STTService()
    with pytest.raises(ValidationFailed, match="empty"):
        stt.process_pasted_transcript("   ")


# ── Issue 8: Backend schema / API error handling ────────────────────────────

def test_action_assign_request_accepts_owner_id():
    """ActionAssignRequest should accept 'owner_id' from frontend (alias for user_id)."""
    from app.api.routes.actions import ActionAssignRequest

    # Test with owner_id (what the frontend sends)
    req = ActionAssignRequest.model_validate({"owner_id": 42})
    assert req.user_id == 42

    # Test with user_id (canonical name)
    req2 = ActionAssignRequest.model_validate({"user_id": 99})
    assert req2.user_id == 99


def test_action_assign_request_null_owner():
    """ActionAssignRequest should accept null to un-assign."""
    from app.api.routes.actions import ActionAssignRequest

    req = ActionAssignRequest.model_validate({"owner_id": None})
    assert req.user_id is None


# ── Issue 9: Eval harness ground-truth count verification ───────────────────

def test_eval_gold_action_counts():
    """Verify the gold benchmark has 3 total actions across 3 meetings."""
    from evals.eval_harness import GOLD_MEETINGS

    total_gold = sum(len(m.get("gold_actions", [])) for m in GOLD_MEETINGS)
    # Meeting 1: 1 action, Meeting 2: 2 actions, Meeting 3: 0 actions = 3 total
    assert total_gold == 3, f"Expected 3 gold actions, got {total_gold}"


def test_eval_match_action_logic():
    """Test that _match_action correctly matches extracted actions to gold by quote and title tokens."""
    from evals.eval_harness import _match_action

    gold = [{"title": "Procure GPU cluster", "quote": "I will procure the GPU cluster by Friday."}]

    # Match by quote substring
    assert _match_action(
        {"title": "GPU cluster procurement", "source_quote": "I will procure the GPU cluster by Friday."},
        gold,
    )

    # Match by title token overlap
    assert _match_action(
        {"title": "Procure the GPU cluster", "source_quote": ""},
        gold,
    )

    # No match for unrelated action
    assert not _match_action(
        {"title": "Order new laptops", "source_quote": "We need new laptops."},
        gold,
    )
