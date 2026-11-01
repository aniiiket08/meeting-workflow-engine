from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.graph import meeting_graph
import app.agents.graph as graph_module
from app.agents.agenda import AgendaItemSchema, TimeboxedAgendaSchema
from app.api.deps import get_db
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.models.agenda import Agenda, AgendaStatus
from app.db.models.room import Room
from app.db.models.user import User, UserRole
from app.main import app
import app.main as main_module
from app.memory.vector_store import memory_store
from app.services.llm import llm_service

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


from app.db.session import SessionLocal, engine as app_engine
import app.observability.tracer as tracer_module

@pytest.fixture(scope="module")
def test_db():
    original_graph_session = graph_module.SessionLocal
    original_tracer_session = tracer_module.SessionLocal
    graph_module.SessionLocal = TestingSessionLocal
    tracer_module.SessionLocal = TestingSessionLocal
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    hashed = get_password_hash("password123")

    users = [
        User(name="Chairman", username="chairman", email="chairman@university.com", role=UserRole.CHAIRMAN, hashed_password=hashed),
        User(name="Principal", username="principal", email="principal@university.com", role=UserRole.PRINCIPAL, hashed_password=hashed),
    ]
    room = Room(name="Boardroom B-204", capacity=20, equipment=["projector"])
    db.add_all(users + [room])
    db.commit()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        graph_module.SessionLocal = original_graph_session
        tracer_module.SessionLocal = original_tracer_session


@pytest.fixture(scope="module")
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    original_start_worker = main_module.start_worker
    original_stop_worker = main_module.stop_worker
    main_module.start_worker = lambda: None
    main_module.stop_worker = lambda: None
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    main_module.start_worker = original_start_worker
    main_module.stop_worker = original_stop_worker


def test_memory_store_retrieval():
    results = memory_store.search("GPU cluster budget", top_k=2)
    assert len(results) > 0
    assert "GPU" in results[0]["text"] or "Lab Equipment" in results[0]["title"]


def _agenda_response(prompt, response_schema, system_prompt=""):
    # Verify the prompt is for the agenda agent (contains meeting title/duration)
    assert "Meeting Duration" in prompt or "agenda" in prompt.lower()
    return response_schema.model_validate(
        {
            "meeting_title": "Test Meeting",
            "total_duration_minutes": 60,
            "items": [
                {
                    "item_number": 1,
                    "title": "Review project status",
                    "owner": "Chairman",
                    "duration_minutes": 30,
                }
            ],
        }
    )


def test_langgraph_execution_and_checkpoint_approval(client, test_db, monkeypatch):
    monkeypatch.setattr(llm_service, "generate_structured", _agenda_response)
    from app.db.models.meeting import Meeting, MeetingStatus
    from datetime import datetime, timezone
    m = Meeting(
        title="Graph Test Meeting",
        duration_minutes=60,
        organizer_id=1,
        status=MeetingStatus.SLOTS_PROPOSED,
        start_time=datetime(2026, 10, 5, 9, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 10, 5, 10, 0, tzinfo=timezone.utc),
    )
    test_db.add(m)
    test_db.commit()
    test_db.refresh(m)

    # Test LangGraph node execution
    config = {"configurable": {"thread_id": "test_meeting_thread_1"}}
    initial_state = {"meeting_id": m.id, "attendees": ["chairman@university.com"], "approval_status": "pending"}

    # Run graph until human approval interrupt node
    state = meeting_graph.invoke(initial_state, config)
    assert "slot" in state
    assert "room" in state
    assert "agenda" in state
    assert state["approval_status"] == "pending"


def test_agenda_approval_endpoint(client, test_db, monkeypatch):
    monkeypatch.setattr(llm_service, "generate_structured", _agenda_response)
    # Login as Chairman
    login_res = client.post("/api/v1/auth/login", json={"username": "chairman", "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create meeting first
    create_res = client.post(
        "/api/v1/meetings",
        json={"title": "Agenda Approval Test", "duration_minutes": 60, "attendee_emails": ["chairman@university.com"]},
        headers=headers,
    )
    meeting_id = create_res.json()["meeting"]["id"]

    # Get agenda (generates draft)
    agenda_res = client.get(f"/api/v1/meetings/{meeting_id}/agenda", headers=headers)
    assert agenda_res.status_code == 200
    agenda_data = agenda_res.json()
    assert isinstance(agenda_data["job_id"], int)
    generated = _agenda_response("agenda", TimeboxedAgendaSchema)
    agenda = Agenda(
        meeting_id=meeting_id,
        items_json=[item.model_dump() for item in generated.items],
        status=AgendaStatus.DRAFT,
    )
    test_db.add(agenda)
    test_db.commit()
    agenda_data = client.get(
        f"/api/v1/meetings/{meeting_id}/agenda", headers=headers
    ).json()
    assert agenda_data["status"] == "draft"

    # Approve agenda via approval gate endpoint
    agenda_id = agenda_data["id"]
    approve_res = client.post(f"/api/v1/agendas/{agenda_id}/approve", headers=headers)
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "approved"
