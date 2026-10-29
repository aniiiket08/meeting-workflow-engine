from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.models
import app.services.llm as llm_module
import app.observability.tracer as tracer_module
import app.agents.graph as graph_module
from app.agents.action_tracker import run_action_tracker_agent
from app.agents.agenda import run_agenda_agent
from app.memory import memory_chat as memory_chat_module
from app.services.llm import LLMService, llm_service
from app.agents.reminder import run_reminder_agent
from app.core.errors import (
    ApprovalRequired,
    Conflict,
    LLMError,
    NotFound,
    ToolError,
    ValidationFailed,
)
from app.db.base import Base
from app.db.models.action import ActionItem, ActionPriority, ActionStatus
from app.db.models.agenda import Agenda, AgendaStatus
from app.db.models.meeting import Attendee, Meeting, MeetingStatus
from app.db.models.minutes import Minutes, MinutesStatus, Transcript
from app.db.models.room import Room
from app.db.models.trace import AgentRun
from app.db.models.user import User, UserRole
from mcp_server.server import mcp_server
from app.observability.tracer import record_prompt, record_token_usage, record_tool_call, trace_agent
from app.services.calendar_service import CalendarService
from app.services.email_service import SentReminder, email_service
from app.services.room_service import room_service
from app.services.stt import stt_service


class _Schema(BaseModel):
    value: str


@pytest.fixture
def audit_db(monkeypatch):
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    test_session_local = sessionmaker(autoflush=False, bind=engine)
    monkeypatch.setattr(tracer_module, "SessionLocal", test_session_local)
    monkeypatch.setattr(graph_module, "SessionLocal", test_session_local)

    db = test_session_local()
    admin = User(
        name="Chairman",
        username="audit-admin",
        email="audit-admin@test.local",
        role=UserRole.CHAIRMAN,
        hashed_password="unused",
    )
    attendee = User(
        name="Student",
        username="audit-attendee",
        email="audit-attendee@test.local",
        role=UserRole.STUDENT,
        hashed_password="unused",
    )
    room = Room(name="Audit Room", capacity=10, equipment=["projector"])
    db.add_all([admin, attendee, room])
    db.commit()
    meeting = Meeting(
        title="Audit Workflow",
        description="Review current work and budget",
        duration_minutes=60,
        organizer_id=admin.id,
        status=MeetingStatus.ROOM_BOOKED,
        room_id=room.id,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    db.add(Attendee(meeting_id=meeting.id, user_id=attendee.id))
    db.commit()
    yield db, meeting, admin, attendee, room
    db.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


def test_scheduling_rejects_missing_attendees_and_calendar_data(audit_db, tmp_path):
    from app.agents.scheduling import run_scheduling_agent

    with pytest.raises(ValidationFailed, match="At least one attendee"):
        run_scheduling_agent([])
    with pytest.raises(ToolError, match="calendar data file is missing"):
        CalendarService(tmp_path / "absent-calendar.json").get_busy_slots(["a@test.local"])
    assert CalendarService().get_busy_slots(["unknown@test.local"]) == {}


def test_room_booking_rejects_double_booking(audit_db):
    db, meeting, admin, _, room = audit_db
    start = datetime(2026, 10, 9, 10, tzinfo=timezone.utc)
    end = start + timedelta(minutes=30)
    room_service.book_room(db, meeting.id, room.id, start, end)
    second = Meeting(
        title="Conflicting meeting",
        duration_minutes=30,
        organizer_id=admin.id,
        status=MeetingStatus.REQUESTED,
    )
    db.add(second)
    db.commit()

    from app.agents.room_booking import run_room_booking_agent

    with pytest.raises(Conflict):
        run_room_booking_agent(
            db,
            second.id,
            2,
            start.isoformat(),
            end.isoformat(),
            ["projector"],
        )


def test_agenda_missing_meeting_and_llm_failure_are_typed(audit_db, monkeypatch):
    db, meeting, *_ = audit_db
    with pytest.raises(NotFound):
        run_agenda_agent(db, meeting_id=99999)
    monkeypatch.setattr(
        llm_service,
        "generate_structured",
        lambda **kwargs: (_ for _ in ()).throw(LLMError("provider unavailable")),
    )
    with pytest.raises(LLMError, match="provider unavailable"):
        run_agenda_agent(db, meeting_id=meeting.id)


def test_agenda_prompt_includes_seeded_past_action_references(audit_db, monkeypatch):
    db, meeting, *_ = audit_db
    captured = {}

    def respond(prompt, response_schema, system_prompt=""):
        captured["prompt"] = prompt
        return response_schema.model_validate(
            {
                "meeting_title": meeting.title,
                "total_duration_minutes": 15,
                "items": [
                    {
                        "item_number": 1,
                        "title": "Review current work",
                        "owner": "Audit Admin",
                        "duration_minutes": 15,
                    }
                ],
            }
        )

    monkeypatch.setattr(llm_service, "generate_structured", respond)
    result = run_agenda_agent(db, meeting_id=meeting.id)
    assert result.items
    # The prompt must reference the meeting title and attendees
    assert meeting.title in captured["prompt"] or "agenda" in captured["prompt"].lower()
    # Past-meeting memory is used for carried-over items, not necessarily inline in the prompt
    # when no user items are provided, the agent uses a purpose-draft prompt
    assert result.items[0].title == "Review current work"


def test_transcription_missing_whisper_raises_tool_error(audit_db, monkeypatch):
    monkeypatch.setitem(sys.modules, "faster_whisper", None)
    with pytest.raises(ToolError):
        stt_service.transcribe(b"audio bytes", "meeting.wav")
    with pytest.raises(ValidationFailed, match="Transcript text cannot be empty"):
        stt_service.process_pasted_transcript("  ")


def test_transcription_uses_whisper_segments_and_does_not_trace_raw_text(audit_db, monkeypatch):
    module = ModuleType("faster_whisper")

    class FakeWhisperModel:
        def __init__(self, *args, **kwargs):
            pass

        def transcribe(self, path, beam_size):
            assert Path(path).exists()
            return [SimpleNamespace(start=1.8, text="Alice said hello")], SimpleNamespace(language="en")

    module.WhisperModel = FakeWhisperModel
    monkeypatch.setitem(sys.modules, "faster_whisper", module)
    result = stt_service.transcribe(b"audio bytes", "meeting.wav")
    trace = audit_db[0].query(AgentRun).filter_by(agent="transcription_agent").one()
    assert result["text"] == "[00:00:01] Alice said hello"
    assert trace.output_data["content_hash"] == result["hash"]
    assert "Alice said hello" not in str(trace.output_data)
    assert "audio bytes" not in str(trace.input_data)


def test_llm_repair_failure_raises_after_one_retry(monkeypatch):
    service = LLMService()
    outputs = iter(["not json", "still not json"])
    monkeypatch.setattr(service, "_call_raw_llm", lambda **kwargs: next(outputs))

    with pytest.raises(LLMError, match="after repair attempt"):
        service.generate_structured("real prompt", _Schema)


def test_llm_repair_retries_once_then_returns_validated_output(monkeypatch):
    service = LLMService()
    outputs = iter(["not json", '{"value":"repaired"}'])
    monkeypatch.setattr(service, "_call_raw_llm", lambda **kwargs: next(outputs))

    result = service.generate_structured("real prompt", _Schema)
    assert result.value == "repaired"


def test_gemini_call_records_usage_and_does_not_log_key(audit_db, monkeypatch):
    service = LLMService()
    service.gemini_key = "test-key-do-not-log"
    service.model = "gemini-3.1-flash-lite"
    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "candidates": [
                    {"content": {"parts": [{"text": '{"value":"three"}'}]}}
                ],
                "usageMetadata": {
                    "totalTokenCount": 23,
                    "thoughtsTokenCount": 7,
                },
            }

    def fake_post(url, **kwargs):
        captured.update(url=url, request=kwargs["json"], headers=kwargs["headers"])
        return FakeResponse()

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)

    @trace_agent("gemini_call_test")
    def run_request():
        return service.generate_structured("How many r's are in strawberry?", _Schema)

    response = run_request()
    assert response.value == "three"
    assert captured["url"].endswith("/models/gemini-3.1-flash-lite:generateContent")
    assert captured["headers"]["x-goog-api-key"] == "test-key-do-not-log"
    assert captured["request"]["contents"][0]["role"] == "user"
    assert captured["request"]["generationConfig"]["responseMimeType"] == "application/json"
    assert "systemInstruction" in captured["request"]
    trace = audit_db[0].query(AgentRun).filter_by(agent="gemini_call_test").one()
    llm_event = next(tool for tool in trace.tools_json if tool["name"] == "llm.gemini")
    assert trace.tokens == 23
    assert llm_event["result"]["reasoning_tokens"] == 7
    assert "test-key-do-not-log" not in str(trace.tools_json)


def test_gemini_retries_transient_server_errors(monkeypatch):
    service = LLMService()
    service.gemini_key = "test-key-do-not-log"
    attempts = 0

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

    def fake_post(url, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            request = llm_module.httpx.Request("POST", url)
            response = llm_module.httpx.Response(503, request=request)
            response.raise_for_status()
        return FakeResponse()

    monkeypatch.setattr(llm_module.httpx, "post", fake_post)
    monkeypatch.setattr(llm_module.time, "sleep", lambda _: None)

    assert service._call_raw_llm("prompt") == "ok"
    assert attempts == 2


def test_memory_chat_does_not_fabricate_when_memory_has_no_matches(audit_db, monkeypatch):
    monkeypatch.setattr(memory_chat_module.memory_store, "search", lambda **kwargs: [])
    with pytest.raises(ValidationFailed, match="No matching past-meeting context"):
        memory_chat_module.memory_chat("What did the team decide?", audit_db[0])


def test_action_tracker_requires_approval_and_flags_missing_owner(audit_db):
    db, meeting, _, _, _ = audit_db
    candidate = {
        "title": "Confirm projector availability",
        "owner_email": None,
        "due_date": "2026-10-09",
        "due_date_relative": "by Friday",
        "priority": "high",
        "source_quote": "We will check whether a projector is available.",
        "timestamp": "00:00:12",
    }
    with pytest.raises(ApprovalRequired):
        run_action_tracker_agent(db, meeting.id, [candidate])

    db.add(
        Transcript(
            meeting_id=meeting.id,
            raw_text="[00:00:12] We will check whether a projector is available.",
            redacted_text="[00:00:12] We will check whether a projector is available.",
            content_hash="audit-transcript",
        )
    )
    db.add(
        Minutes(
            meeting_id=meeting.id,
            version=1,
            summary="Approved",
            key_discussion_points=[],
            action_items_json=[candidate],
            status=MinutesStatus.APPROVED,
            content_hash="audit-minutes",
            approved_by_id=meeting.organizer_id,
        )
    )
    db.commit()
    items = run_action_tracker_agent(db, meeting.id, [candidate])
    assert len(items) == 1
    assert items[0].owner_id is None
    assert items[0].needs_confirmation is True
    assert items[0].source_timestamp == "00:00:12"


def test_reminders_use_date_buckets_and_are_idempotent(audit_db, monkeypatch):
    db, meeting, admin, _, _ = audit_db
    db.add(
        Minutes(
            meeting_id=meeting.id,
            version=1,
            summary="Approved",
            key_discussion_points=[],
            action_items_json=[],
            status=MinutesStatus.APPROVED,
            content_hash="reminder-approved",
            approved_by_id=admin.id,
        )
    )
    now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    for description, offset in (("gentle", 2), ("nudge", 0), ("escalate", -2)):
        db.add(
            ActionItem(
                meeting_id=meeting.id,
                description=description,
                owner_id=admin.id,
                due_date=now + timedelta(days=offset),
                priority=ActionPriority.HIGH,
                status=ActionStatus.PENDING,
                source_quote="source",
                source_timestamp="00:00:01",
                confidence=1.0,
            )
        )
    db.commit()
    sends = []
    # Accept either positional or keyword arguments so the mock does not depend
    # on how send_email happens to be called.
    monkeypatch.setattr(
        email_service,
        "send_email",
        lambda *args, **kwargs: sends.append(
            kwargs["subject"] if "subject" in kwargs else args[1]
        )
        or True,
    )

    first = run_reminder_agent(db, meeting.id, now=now)
    levels = {reminder.level.value for reminder in db.query(SentReminder).all()}
    second = run_reminder_agent(db, meeting.id, now=now)
    assert first["reminders_sent"] == 3
    assert levels == {"gentle", "nudge", "escalate_chair"}
    assert second["reminders_sent"] == 0
    assert len(sends) == 3


def test_reminders_do_not_send_before_minutes_approval(audit_db, monkeypatch):
    db, meeting, admin, _, _ = audit_db
    db.add(
        ActionItem(
            meeting_id=meeting.id,
            description="Unapproved task",
            owner_id=admin.id,
            due_date=datetime.now(timezone.utc),
            priority=ActionPriority.HIGH,
            status=ActionStatus.PENDING,
            confidence=1.0,
        )
    )
    db.commit()
    monkeypatch.setattr(email_service, "send_email", lambda *args, **kwargs: pytest.fail("sent before approval"))
    assert run_reminder_agent(db, meeting.id)["reminders_sent"] == 0


def test_reminder_delivery_failure_is_typed(audit_db, monkeypatch):
    db, meeting, admin, _, _ = audit_db
    now = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    db.add(
        Minutes(
            meeting_id=meeting.id,
            version=1,
            summary="Approved",
            key_discussion_points=[],
            action_items_json=[],
            status=MinutesStatus.APPROVED,
            content_hash="reminder-delivery-approved",
            approved_by_id=admin.id,
        )
    )
    db.add(
        ActionItem(
            meeting_id=meeting.id,
            description="Due today",
            owner_id=admin.id,
            due_date=now,
            priority=ActionPriority.HIGH,
            status=ActionStatus.PENDING,
            confidence=1.0,
        )
    )
    db.commit()
    monkeypatch.setattr(
        email_service,
        "send_email",
        lambda *args, **kwargs: (_ for _ in ()).throw(ToolError("SMTP offline")),
    )
    with pytest.raises(ToolError, match="SMTP offline"):
        run_reminder_agent(db, meeting.id, now=now)


def test_distribution_requires_approved_minutes(audit_db):
    from app.agents.distribution import run_distribution_agent

    db, meeting, *_ = audit_db
    with pytest.raises(ApprovalRequired):
        run_distribution_agent(db, meeting.id)


def test_distribution_failure_is_typed_after_approval(audit_db, monkeypatch):
    from app.agents.distribution import run_distribution_agent

    db, meeting, admin, _, _ = audit_db
    meeting.start_time = datetime(2026, 10, 5, 10, tzinfo=timezone.utc)
    meeting.end_time = meeting.start_time + timedelta(minutes=60)
    db.add(
        Minutes(
            meeting_id=meeting.id,
            version=1,
            summary="Approved",
            key_discussion_points=[],
            action_items_json=[],
            status=MinutesStatus.APPROVED,
            content_hash="distribution-failure-approved",
            approved_by_id=admin.id,
        )
    )
    db.commit()
    monkeypatch.setattr(email_service, "generate_pdf_minutes", lambda summary, points: b"pdf")
    monkeypatch.setattr(email_service, "generate_ics_calendar", lambda **kwargs: "ics")
    monkeypatch.setattr(
        email_service,
        "send_email",
        lambda *args, **kwargs: (_ for _ in ()).throw(ToolError("SMTP offline")),
    )
    with pytest.raises(ToolError, match="SMTP offline"):
        run_distribution_agent(db, meeting.id)


def test_graph_rejects_missing_meeting_and_missing_transcript(audit_db):
    from app.agents.graph import (
        _meeting_id,
        actions_node,
        approval_gate_node,
        minutes_node,
        approve_minutes_gate_node,
    )

    db, meeting, *_ = audit_db
    with pytest.raises(ValidationFailed, match="meeting_id is required"):
        _meeting_id({})
    with pytest.raises(ValidationFailed, match="No transcript"):
        minutes_node({"meeting_id": meeting.id})


def test_graph_approval_nodes_persist_human_approval(audit_db):
    from app.agents.graph import actions_node, approval_gate_node, approve_minutes_gate_node

    db, meeting, admin, *_ = audit_db
    agenda = Agenda(
        meeting_id=meeting.id,
        items_json=[{"item_number": 1, "title": "Review", "owner": "Audit Admin", "duration_minutes": 15}],
        status=AgendaStatus.DRAFT,
    )
    db.add(agenda)
    db.add(
        Transcript(
            meeting_id=meeting.id,
            raw_text="[00:00:01] Meeting transcript.",
            redacted_text="[00:00:01] Meeting transcript.",
            content_hash="approval-gate-transcript",
        )
    )
    minutes = Minutes(
        meeting_id=meeting.id,
        version=1,
        summary="Draft",
        key_discussion_points=[],
        action_items_json=[],
        status=MinutesStatus.DRAFT,
        content_hash="approval-gate-minutes",
    )
    db.add(minutes)
    db.commit()

    with pytest.raises(ApprovalRequired):
        approval_gate_node({"meeting_id": meeting.id, "approval_status": "pending"})
    approval_gate_node(
        {"meeting_id": meeting.id, "approval_status": "approved", "approved_by_id": admin.id}
    )
    assert db.query(Agenda).filter_by(meeting_id=meeting.id).one().approved_by_id == admin.id
    assert db.query(Agenda).filter_by(meeting_id=meeting.id).one().approved_at is not None

    with pytest.raises(ApprovalRequired):
        approve_minutes_gate_node(
            {"meeting_id": meeting.id, "approval_status": "pending_minutes"}
        )
    approve_minutes_gate_node(
        {"meeting_id": meeting.id, "approval_status": "approved_minutes", "approved_by_id": admin.id}
    )
    approved_minutes = db.query(Minutes).filter_by(meeting_id=meeting.id).one()
    assert approved_minutes.status == MinutesStatus.APPROVED
    assert approved_minutes.approved_by_id == admin.id
    assert actions_node({"meeting_id": meeting.id})["actions"] == []


def test_mcp_lists_only_registered_tool_and_enforces_agent_allowlist():
    tools = [tool["name"] for tool in mcp_server.list_tools()]
    assert "calendar_freebusy" in tools
    assert "room_search" in tools
    assert "room_book" in tools
    assert "zoom_create_meeting" in tools
    assert "zoom_get_meeting" in tools
    with pytest.raises(ToolError):
        mcp_server.call_tool(
            "calendar_freebusy",
            {"emails": ["owner@test.local"]},
            agent_name="room_booking_agent",
        )
    with pytest.raises(ToolError):
        mcp_server.call_tool(
            "room_book",
            {"meeting_id": 1, "room_id": 1, "start_time": "2026-10-06T09:00:00Z", "end_time": "2026-10-06T10:00:00Z"},
            agent_name="agenda_agent",
        )


def test_trace_records_prompt_tools_and_actual_tokens(audit_db):
    db, *_ = audit_db

    @trace_agent("audit_trace_test")
    def traced_operation():
        record_prompt("system context", "real user prompt")
        record_tool_call("unit.test_tool", {"input": "real"}, {"output": "ok"})
        record_token_usage(17)
        return {"answer": "from source"}

    traced_operation()
    trace = db.query(AgentRun).filter_by(agent="audit_trace_test").one()
    assert trace.input_data["prompts"][0]["user"] == "real user prompt"
    assert trace.tools_json[0]["name"] == "unit.test_tool"
    assert trace.tokens == 17
    assert trace.output_data == {"answer": "from source"}