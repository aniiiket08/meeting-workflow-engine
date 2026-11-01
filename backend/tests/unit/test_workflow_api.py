from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.routes import agendas as agendas_route
from app.api.routes import minutes as minutes_route
from app.agents.agenda import AgendaItemSchema, TimeboxedAgendaSchema
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.models.action import ActionItem, ActionPriority, ActionStatus
from app.db.models.agenda import Agenda, AgendaStatus
from app.db.models.audit import AuditLog
from app.db.models.meeting import Attendee, Meeting, MeetingStatus
from app.db.models.minutes import Minutes, MinutesStatus, Transcript
from app.db.models.room import Room
from app.db.models.trace import AgentRun
from app.db.models.user import User, UserRole
from app.main import app
import app.main as main_module
import app.services.job_worker as job_worker
from app.services.email_service import email_service
from app.services.email_service import SentReminder
import app.observability.tracer as tracer


engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autoflush=False, bind=engine)


@pytest.fixture
def workflow_client(monkeypatch):
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    monkeypatch.setattr(tracer, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(job_worker, "SessionLocal", TestingSessionLocal)
    monkeypatch.setattr(main_module, "start_worker", lambda: None)
    monkeypatch.setattr(main_module, "stop_worker", lambda: None)
    monkeypatch.setattr(
        minutes_route,
        "run_minutes_agent",
        lambda transcript_text, meeting_id=None: {
            "summary": "The team agreed on a follow-up.",
            "key_discussion_points": ["A report is needed."],
            "decisions": [
                {
                    "text": "Prepare the report by October 20.",
                    "source_quote": "I will prepare the report by October 20.",
                    "timestamp": "00:00:10",
                }
            ],
            "action_items": [
                {
                    "title": "Prepare the report",
                    "owner_email": "hod@university.com",
                    # Relative to today on purpose: a fixed date would eventually
                    # fall inside a reminder bucket and expire this test.
                    "due_date": (
                        datetime.now(timezone.utc) + timedelta(days=30)
                    ).date().isoformat(),
                    "due_date_relative": "by October 20",
                    "priority": "high",
                    "source_quote": "I will prepare the report by October 20.",
                    "timestamp": "00:00:10",
                }
            ],
            "content_hash": "test-content-hash",
        },
    )

    password_hash = get_password_hash("password123")
    users = [
        User(name="Chairman", username="chairman", email="chairman@university.com", role=UserRole.CHAIRMAN, hashed_password=password_hash),
        User(name="Principal", username="principal", email="principal@university.com", role=UserRole.PRINCIPAL, hashed_password=password_hash),
        User(name="HOD", username="hod", email="hod@university.com", role=UserRole.HOD, hashed_password=password_hash),
        User(name="Teacher", username="teacher", email="teacher@university.com", role=UserRole.TEACHER, hashed_password=password_hash),
        User(name="Aniket", username="aniket", email="aniket@university.com", role=UserRole.STUDENT, hashed_password=password_hash),
        User(name="Sujal", username="sujal", email="sujal@university.com", role=UserRole.STUDENT, hashed_password=password_hash),
        User(name="Viraj", username="viraj", email="viraj@university.com", role=UserRole.STUDENT, hashed_password=password_hash),
        User(name="Sarvesh", username="sarvesh", email="sarvesh@university.com", role=UserRole.STUDENT, hashed_password=password_hash),
    ]
    users_by_username = {user.username: user for user in users}
    user = users_by_username["hod"]
    attendee = users_by_username["aniket"]
    chairman = users_by_username["chairman"]
    teacher = users_by_username["teacher"]
    room = Room(name="Test Room", capacity=10, equipment=[])
    db.add_all([*users, room])
    db.commit()

    meeting = Meeting(
        title="Workflow Test",
        duration_minutes=60,
        organizer_id=user.id,
        room_id=room.id,
        status=MeetingStatus.ROOM_BOOKED,
    )
    db.add(meeting)
    db.commit()
    db.refresh(meeting)
    db.add_all(
        Attendee(meeting_id=meeting.id, user_id=member.id)
        for member in (user, attendee, teacher)
    )
    db.add(
        Transcript(
            meeting_id=meeting.id,
            raw_text="[00:00:10] I will prepare the report by October 20.",
            redacted_text="[00:00:10] I will prepare the report by October 20.",
            content_hash="test-transcript-hash",
        )
    )
    db.commit()

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client, db, meeting.id
    app.dependency_overrides.clear()
    db.close()
    Base.metadata.drop_all(bind=engine)


def _process_next_job(db):
    assert job_worker._run_one()
    db.expire_all()


def test_pasted_transcript_api_redacts_and_generates_minutes(workflow_client, monkeypatch):
    client, db, meeting_id = workflow_client
    agent = minutes_route.run_minutes_agent
    captured = {}

    def capture_redacted_input(transcript_text, meeting_id=None):
        captured["transcript"] = transcript_text
        return agent(transcript_text=transcript_text, meeting_id=meeting_id)

    monkeypatch.setattr(minutes_route, "run_minutes_agent", capture_redacted_input)
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "hod", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    transcript_text = "[00:00:10] Contact alice@example.com. I will prepare the report by October 20."

    response = client.post(
        f"/api/v1/meetings/{meeting_id}/transcript/paste",
        headers=headers,
        json={"text": transcript_text},
    )

    assert response.status_code == 200
    job_id = response.json()["job_id"]
    _process_next_job(db)
    job_response = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert job_response.status_code == 200
    result = job_response.json()["result"]
    assert result["status"] == "processed"
    assert "[REDACTED_EMAIL]" in result["redacted_text"]
    transcript = db.query(Transcript).filter_by(meeting_id=meeting_id).one()
    assert transcript.raw_text == transcript_text
    assert "alice@example.com" not in transcript.redacted_text
    assert "[REDACTED_EMAIL]" in captured["transcript"]
    assert "alice@example.com" not in captured["transcript"]
    assert db.query(Meeting).filter_by(id=meeting_id).one().status == MeetingStatus.MINUTES_DRAFTED

    minutes_response = client.get(
        f"/api/v1/meetings/{meeting_id}/minutes", headers=headers
    )
    assert minutes_response.status_code == 200
    assert minutes_response.json()["summary"] == "The team agreed on a follow-up."
    assert "Decision: Prepare the report by October 20." in minutes_response.json()["key_discussion_points"]
    assert minutes_response.json()["transcript"] == transcript.redacted_text
    assert minutes_response.json()["action_items"][0]["title"] == "Prepare the report"
    assert db.query(Minutes).filter_by(meeting_id=meeting_id).count() == 1
    assert db.query(ActionItem).filter_by(meeting_id=meeting_id).count() == 1
    actions_response = client.get("/api/v1/actions", headers=headers)
    assert actions_response.status_code == 200
    generated_action = next(
        item for item in actions_response.json() if item["meeting_id"] == meeting_id
    )
    assert generated_action["description"] == "Prepare the report"
    assert generated_action["status"] == "pending"


def test_audio_transcript_upload_api_persists_transcription(workflow_client, monkeypatch):
    client, db, meeting_id = workflow_client
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "hod", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    monkeypatch.setattr(
        minutes_route.stt_service,
        "transcribe",
        lambda audio_bytes, filename: {
            "text": "[00:00:02] We agreed to publish the report.",
            "language": "en",
            "hash": "uploaded-transcript-hash",
        },
    )

    response = client.post(
        f"/api/v1/meetings/{meeting_id}/transcript/upload",
        headers=headers,
        files={"file": ("meeting.wav", b"audio bytes", "audio/wav")},
    )

    assert response.status_code == 200
    job_id = response.json()["job_id"]
    _process_next_job(db)
    assert client.get(f"/api/v1/jobs/{job_id}", headers=headers).json()["status"] == "completed"
    transcript = db.query(Transcript).filter_by(meeting_id=meeting_id).one()
    assert transcript.redacted_text == "[00:00:02] We agreed to publish the report."
    assert transcript.content_hash == "uploaded-transcript-hash"
    assert db.query(Meeting).filter_by(id=meeting_id).one().status == MeetingStatus.MINUTES_DRAFTED


def test_minutes_approval_creates_follow_up_tasks_and_activity(workflow_client, monkeypatch):
    client, db, meeting_id = workflow_client
    delivery_keys = []
    monkeypatch.setattr(
        email_service,
        "send_email",
        lambda *args, **kwargs: delivery_keys.append(kwargs["idempotency_key"]) or True,
    )
    monkeypatch.setattr(email_service, "generate_pdf_minutes", lambda summary, points: b"pdf-test")
    monkeypatch.setattr(email_service, "generate_ics_calendar", lambda **kwargs: "ics-test")
    attendee_login = client.post(
        "/api/v1/auth/login",
        json={"username": "aniket", "password": "password123"},
    )
    attendee_headers = {
        "Authorization": f"Bearer {attendee_login.json()['access_token']}"
    }
    assert client.post(
        f"/api/v1/meetings/{meeting_id}/minutes/approve",
        headers=attendee_headers,
    ).status_code == 403
    assert client.get("/api/v1/traces", headers=attendee_headers).status_code == 403
    assert db.query(ActionItem).filter_by(meeting_id=meeting_id).count() == 0

    login = client.post(
        "/api/v1/auth/login",
        json={"username": "hod", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    draft_response = client.get(
        f"/api/v1/meetings/{meeting_id}/minutes", headers=headers
    )
    assert draft_response.status_code == 200
    _process_next_job(db)
    draft_response = client.get(
        f"/api/v1/meetings/{meeting_id}/minutes", headers=headers
    )
    draft = draft_response.json()
    assert draft["action_items"][0]["title"] == "Prepare the report"
    assert db.query(ActionItem).filter_by(meeting_id=meeting_id).count() == 1

    approval_response = client.post(
        f"/api/v1/meetings/{meeting_id}/minutes/approve", headers=headers
    )
    assert approval_response.status_code == 403

    chairman_login = client.post(
        "/api/v1/auth/login",
        json={"username": "chairman", "password": "password123"},
    )
    chairman_headers = {"Authorization": f"Bearer {chairman_login.json()['access_token']}"}
    approval_response = client.post(
        f"/api/v1/meetings/{meeting_id}/minutes/approve", headers=chairman_headers
    )
    assert approval_response.status_code == 200
    approval_job_id = approval_response.json()["job_id"]
    _process_next_job(db)
    completed_job = client.get(
        f"/api/v1/jobs/{approval_job_id}", headers=chairman_headers
    ).json()
    assert completed_job["status"] == "completed"
    assert completed_job["result"]["distribution"]["status"] == "distributed"
    assert db.query(ActionItem).filter_by(meeting_id=meeting_id).count() == 1
    action = db.query(ActionItem).filter_by(meeting_id=meeting_id).one()
    assert action.source_timestamp == "00:00:10"
    assert db.query(AgentRun).filter_by(meeting_id=meeting_id).count() >= 2
    assert db.query(AuditLog).filter_by(action="DISTRIBUTE_MINUTES").count() == 1
    assert db.query(SentReminder).count() == 0

    retry_response = client.post(
        f"/api/v1/meetings/{meeting_id}/minutes/approve", headers=chairman_headers
    )
    assert retry_response.status_code == 200
    retry_job_id = retry_response.json()["job_id"]
    _process_next_job(db)
    assert client.get(
        f"/api/v1/jobs/{retry_job_id}", headers=chairman_headers
    ).json()["result"]["distribution"]["status"] == "already_distributed"
    assert db.query(ActionItem).filter_by(meeting_id=meeting_id).count() == 1
    assert len(delivery_keys) == 3


def test_agenda_api_uses_editable_items_contract(workflow_client, monkeypatch):
    client, db, meeting_id = workflow_client
    monkeypatch.setattr(
        agendas_route,
        "run_agenda_agent",
        lambda db, meeting_id, **kwargs: TimeboxedAgendaSchema(
            meeting_title="Workflow Test",
            total_duration_minutes=60,
            items=[
                AgendaItemSchema(
                    item_number=1,
                    title="Review progress",
                    owner="HOD",
                    duration_minutes=30,
                )
            ],
        ),
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "hod", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = client.get(f"/api/v1/meetings/{meeting_id}/agenda", headers=headers)
    assert response.status_code == 200
    _process_next_job(db)
    agenda = client.get(f"/api/v1/meetings/{meeting_id}/agenda", headers=headers).json()
    assert agenda["items"][0]["title"] == "Review progress"

    agenda["items"][0]["title"] = "Review completed work"
    updated = client.put(
        f"/api/v1/meetings/{meeting_id}/agenda",
        headers=headers,
        json={"items": agenda["items"]},
    )
    assert updated.status_code == 200
    assert updated.json()["items"][0]["title"] == "Review completed work"

    approved = client.post(
        f"/api/v1/agendas/{agenda['id']}/approve", headers=headers
    )
    assert approved.status_code == 403

    chairman_login = client.post(
        "/api/v1/auth/login",
        json={"username": "chairman", "password": "password123"},
    )
    chairman_headers = {"Authorization": f"Bearer {chairman_login.json()['access_token']}"}
    approved = client.post(
        f"/api/v1/agendas/{agenda['id']}/approve", headers=chairman_headers
    )
    assert approved.status_code == 200
    assert approved.json()["items"][0]["title"] == "Review completed work"


def test_university_role_permissions_for_meetings_agenda_and_actions(workflow_client):
    client, db, meeting_id = workflow_client
    users = {user.username: user for user in db.query(User).all()}
    agenda = Agenda(
        meeting_id=meeting_id,
        items_json=[{"item_number": 1, "title": "Review draft", "owner": "HOD", "duration_minutes": 20}],
        status=AgendaStatus.DRAFT,
    )
    teacher_task = ActionItem(
        meeting_id=meeting_id,
        description="Review the draft",
        owner_id=users["teacher"].id,
        owner_name="Teacher",
        owner_email=users["teacher"].email,
        status=ActionStatus.PENDING,
        priority=ActionPriority.MEDIUM,
    )
    student_task = ActionItem(
        meeting_id=meeting_id,
        description="Collect feedback",
        owner_id=users["aniket"].id,
        owner_name="Aniket",
        owner_email=users["aniket"].email,
        status=ActionStatus.PENDING,
        priority=ActionPriority.LOW,
    )
    db.add_all([agenda, teacher_task, student_task])
    db.commit()

    def headers(username):
        response = client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": "password123"},
        )
        assert response.status_code == 200
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    chairman_headers = headers("chairman")
    principal_headers = headers("principal")
    hod_headers = headers("hod")
    teacher_headers = headers("teacher")
    aniket_headers = headers("aniket")
    sujal_headers = headers("sujal")
    viraj_headers = headers("viraj")
    sarvesh_headers = headers("sarvesh")

    for username, manager_headers in (
        ("chairman", chairman_headers),
        ("principal", principal_headers),
        ("hod", hod_headers),
    ):
        scheduled = client.post(
            "/api/v1/meetings",
            headers=manager_headers,
            json={"title": f"{username.title()} scheduled meeting", "attendee_emails": []},
        )
        assert scheduled.status_code == 200

    for student_headers in (aniket_headers, sujal_headers, viraj_headers, sarvesh_headers):
        denied = client.post(
            "/api/v1/meetings",
            headers=student_headers,
            json={"title": "Student-created meeting", "attendee_emails": []},
        )
        assert denied.status_code == 403

    denied_schedule = client.post(
        "/api/v1/meetings",
        headers=aniket_headers,
        json={"title": "Student-created meeting", "attendee_emails": []},
    )
    assert denied_schedule.status_code == 403
    teacher_schedule = client.post(
        "/api/v1/meetings",
        headers=teacher_headers,
        json={
            "title": "Teacher-created meeting",
            "attendee_emails": ["aniket@university.com"],
        },
    )
    assert teacher_schedule.status_code == 200
    assert any(
        item["id"] == teacher_schedule.json()["meeting"]["id"]
        for item in client.get("/api/v1/meetings", headers=teacher_headers).json()
    )

    for manager_headers in (chairman_headers, principal_headers, hod_headers):
        meeting_list = client.get("/api/v1/meetings", headers=manager_headers)
        assert any(item["id"] == meeting_id for item in meeting_list.json())
        assert len(client.get("/api/v1/actions", headers=manager_headers).json()) == 2

    for participant_headers in (teacher_headers, aniket_headers):
        meeting_list = client.get("/api/v1/meetings", headers=participant_headers)
        assert any(item["id"] == meeting_id for item in meeting_list.json())
        assert client.get(f"/api/v1/meetings/{meeting_id}/agenda", headers=participant_headers).status_code == 200
        assert client.get(f"/api/v1/meetings/{meeting_id}/minutes", headers=participant_headers).status_code == 200

    for uninvited_headers in (sujal_headers, viraj_headers, sarvesh_headers):
        meeting_list = client.get("/api/v1/meetings", headers=uninvited_headers)
        assert all(item["id"] != meeting_id for item in meeting_list.json())
        assert client.get(f"/api/v1/meetings/{meeting_id}/agenda", headers=uninvited_headers).status_code == 403
        assert client.get(f"/api/v1/meetings/{meeting_id}/minutes", headers=uninvited_headers).status_code == 403

    assert len(client.get("/api/v1/actions", headers=teacher_headers).json()) == 1
    assert len(client.get("/api/v1/actions", headers=aniket_headers).json()) == 1
    for unassigned_student_headers in (sujal_headers, viraj_headers, sarvesh_headers):
        assert client.get("/api/v1/actions", headers=unassigned_student_headers).json() == []

    agenda_update = {
        "items": [{"item_number": 1, "title": "Updated topic", "owner": "HOD", "duration_minutes": 25}]
    }
    for restricted_headers in (teacher_headers, aniket_headers):
        assert client.put(
            f"/api/v1/meetings/{meeting_id}/agenda",
            headers=restricted_headers,
            json=agenda_update,
        ).status_code == 403
    assert client.put(
        f"/api/v1/meetings/{meeting_id}/agenda",
        headers=hod_headers,
        json=agenda_update,
    ).status_code == 200
    assert client.post(
        f"/api/v1/agendas/{agenda.id}/approve", headers=principal_headers
    ).status_code == 403
    assert client.post(
        f"/api/v1/agendas/{agenda.id}/approve", headers=chairman_headers
    ).status_code == 200

    assert client.put(
        f"/api/v1/actions/{student_task.id}/status",
        headers=teacher_headers,
        json={"status": "completed"},
    ).status_code == 403
    assert client.put(
        f"/api/v1/actions/{student_task.id}/status",
        headers=aniket_headers,
        json={"status": "completed"},
    ).status_code == 200
    assert client.put(
        f"/api/v1/actions/{teacher_task.id}/status",
        headers=teacher_headers,
        json={"status": "in_progress"},
    ).status_code == 200
    assert client.put(
        f"/api/v1/actions/{teacher_task.id}/status",
        headers=teacher_headers,
        json={"status": "blocked"},
    ).status_code == 422
    assert client.put(
        f"/api/v1/actions/{student_task.id}/assign",
        headers=aniket_headers,
        json={"user_id": users["sujal"].id},
    ).status_code == 403
    assigned = client.put(
        f"/api/v1/actions/{teacher_task.id}/assign",
        headers=hod_headers,
        json={"user_id": users["sujal"].id},
    )
    assert assigned.status_code == 200
    assert assigned.json()["owner_id"] == users["sujal"].id
    assert len(client.get("/api/v1/actions", headers=teacher_headers).json()) == 0
    assert len(client.get("/api/v1/actions", headers=sujal_headers).json()) == 1