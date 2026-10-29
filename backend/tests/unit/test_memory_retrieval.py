from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.models.agenda import Decision
from app.db.models.meeting import Meeting, MeetingStatus
from app.db.models.minutes import Minutes, MinutesStatus
from app.db.models.user import User, UserRole
from app.memory.vector_store import MemoryStore
from app.memory.memory_chat import memory_chat


@pytest.fixture
def memory_test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSession()

    user = User(name="Chairman", username="chairman", email="chairman@university.com", role=UserRole.CHAIRMAN, hashed_password="pw")
    db.add(user)
    db.commit()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_memory_store_retrieves_relevant_seed_meeting():
    store = MemoryStore()
    results = store.search("GPU cluster budget", top_k=3)
    assert len(results) >= 1
    assert any("GPU cluster" in r["text"] for r in results)
    assert any("15,000" in r["text"] for r in results)


def test_memory_store_unrelated_query_returns_empty():
    store = MemoryStore()
    results = store.search("astronomy spacecraft orbit trajectory propulsion", top_k=3)
    assert results == []


def test_newly_completed_meeting_becomes_searchable(memory_test_db):
    db = memory_test_db
    chairman = db.query(User).filter_by(username="chairman").one()

    # Create and complete a new meeting
    meeting = Meeting(
        title="Autonomous Driving Lab Setup",
        duration_minutes=60,
        organizer_id=chairman.id,
        status=MeetingStatus.MINUTES_APPROVED,
        start_time=datetime(2026, 10, 20, 11, 0, tzinfo=timezone.utc),
    )
    db.add(meeting)
    db.commit()

    minutes = Minutes(
        meeting_id=meeting.id,
        version=1,
        summary="Finalized LiDAR sensors and autonomous driving workstation procurement.",
        key_discussion_points=["Ordered 2 Velodyne LiDAR units for the test track."],
        status=MinutesStatus.APPROVED,
        content_hash="hash-123",
    )
    decision = Decision(
        meeting_id=meeting.id,
        text="Allocate $8,000 for Velodyne LiDAR units",
        source_quote="Allocate $8,000 for Velodyne LiDAR units",
    )
    db.add_all([minutes, decision])
    db.commit()

    store = MemoryStore()
    # Query before sync should not find the new meeting
    res_before = store.search("Velodyne LiDAR", top_k=3)
    assert not any(r.get("meeting_id") == meeting.id for r in res_before)

    # Search with db session automatically syncs approved meetings
    res_after = store.search("Velodyne LiDAR", top_k=3, db=db)
    assert len(res_after) >= 1
    assert any(r.get("meeting_id") == meeting.id for r in res_after)
    assert any("LiDAR" in r["text"] for r in res_after)


def test_memory_chat_agent_with_new_meeting_context(memory_test_db, monkeypatch):
    from app.services.llm import llm_service
    from app.memory import vector_store

    db = memory_test_db
    chairman = db.query(User).filter_by(username="chairman").one()

    meeting = Meeting(
        title="Solar Panel Grant",
        duration_minutes=60,
        organizer_id=chairman.id,
        status=MeetingStatus.MINUTES_APPROVED,
        start_time=datetime(2026, 10, 25, 14, 0, tzinfo=timezone.utc),
    )
    db.add(meeting)
    db.commit()

    minutes = Minutes(
        meeting_id=meeting.id,
        version=1,
        summary="Received $50,000 grant for rooftop solar panels.",
        status=MinutesStatus.APPROVED,
        content_hash="hash-solar",
    )
    db.add(minutes)
    db.commit()

    # Sync into global memory_store
    vector_store.memory_store.sync_from_database(db)

    from app.memory.memory_chat import MemoryChatResponse

    def mock_gen_structured(*args, **kwargs):
        return MemoryChatResponse(
            answer="The university received a $50,000 solar panel grant.",
            citations=["Solar Panel Grant"],
        )

    monkeypatch.setattr(llm_service, "generate_structured", mock_gen_structured)
    response = memory_chat("What grant was approved for solar panels?", db)
    assert "solar" in response["answer"].lower()
    assert response["citations"] == ["Solar Panel Grant"]
