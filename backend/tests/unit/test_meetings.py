from datetime import date, datetime, timedelta, timezone
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.models.meeting import Attendee, Meeting, MeetingStatus
from app.db.models.room import Room
from app.db.models.user import User, UserRole
from app.main import app
from app.services.room_service import room_service
import app.observability.tracer as tracer_module

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def test_db():
    original_tracer_session = tracer_module.SessionLocal
    tracer_module.SessionLocal = TestingSessionLocal
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    hashed = get_password_hash("password123")
    
    # Seed users and room
    users = [
        User(name="Chairman", username="chairman", email="chairman@university.com", role=UserRole.CHAIRMAN, hashed_password=hashed),
        User(name="Aniket", username="aniket", email="aniket@university.com", role=UserRole.STUDENT, hashed_password=hashed),
    ]
    room = Room(name="Conference Room A-101", capacity=10, equipment=["projector"])
    db.add_all(users + [room])
    db.commit()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        tracer_module.SessionLocal = original_tracer_session


@pytest.fixture(scope="module")
def client(test_db):
    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_meeting_creation_and_slot_ranking(client, test_db):
    # Login first
    login_res = client.post("/api/v1/auth/login", json={"username": "chairman", "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Post new meeting request
    target_date = date.today() + timedelta(days=2)
    create_res = client.post(
        "/api/v1/meetings",
        json={
            "title": "Quarterly Strategy Sync",
            "description": "Discuss Q4 objectives and budget",
            "duration_minutes": 60,
            "target_date": target_date.isoformat(),
            "attendee_emails": [
                "aniket@university.com",
                "external.guest@gmail.com",
            ],
            "equipment_needed": ["projector"],
        },
        headers=headers,
    )
    assert create_res.status_code == 200
    data = create_res.json()
    assert "meeting" in data
    assert "slots" in data
    assert len(data["slots"]) == 3
    assert "reason" in data["slots"][0]
    meeting = test_db.query(Meeting).filter_by(id=data["meeting"]["id"]).one()
    assert meeting.target_date == target_date
    assert meeting.equipment_needed == ["projector"]
    attendee_emails = {
        attendee.user.email if attendee.user else attendee.external_email
        for attendee in test_db.query(Attendee).filter_by(meeting_id=meeting.id).all()
    }
    assert attendee_emails == {
        "chairman@university.com",
        "aniket@university.com",
        "external.guest@gmail.com",
    }


def test_confirm_slot_and_room_booking(client):
    # Login
    login_res = client.post("/api/v1/auth/login", json={"username": "chairman", "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create meeting
    create_res = client.post(
        "/api/v1/meetings",
        json={
            "title": "Room Booking Test Sync",
            "duration_minutes": 60,
            "attendee_emails": ["aniket@university.com"],
        },
        headers=headers,
    )
    meeting_id = create_res.json()["meeting"]["id"]
    slots = create_res.json()["slots"]

    # Confirm slot
    confirm_res = client.post(
        f"/api/v1/meetings/{meeting_id}/confirm",
        json={
            "selected_start_time": slots[0]["start_time"],
            "selected_end_time": slots[0]["end_time"],
        },
        headers=headers,
    )
    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()
    assert confirm_data["meeting"]["status"] == "room_booked"
    confirmed_start = datetime.fromisoformat(confirm_data["meeting"]["start_time"])
    assert confirmed_start.utcoffset() == timedelta(0)
    assert confirm_data["room_booking"]["status"] == "booked"
    assert confirm_data["room_booking"]["room"]["name"] == "Conference Room A-101"


def test_confirm_slot_zoom_online_booking(client):
    login_res = client.post("/api/v1/auth/login", json={"username": "chairman", "password": "password123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post(
        "/api/v1/meetings",
        json={
            "title": "Online Zoom Test Meeting",
            "duration_minutes": 30,
            "attendee_emails": ["aniket@university.com"],
        },
        headers=headers,
    )
    meeting_id = create_res.json()["meeting"]["id"]
    slots = create_res.json()["slots"]

    confirm_res = client.post(
        f"/api/v1/meetings/{meeting_id}/confirm",
        json={
            "selected_start_time": slots[0]["start_time"],
            "selected_end_time": slots[0]["end_time"],
            "is_online": True,
        },
        headers=headers,
    )
    assert confirm_res.status_code == 200
    confirm_data = confirm_res.json()
    assert confirm_data["meeting"]["status"] == "room_booked"
    assert confirm_data["room_booking"]["status"] == "online"
    assert "zoom" in confirm_data["room_booking"]
    assert confirm_data["meeting"]["zoom_meeting_id"] is not None
    assert "https://zoom.us/j/" in confirm_data["meeting"]["zoom_join_url"]


def test_authenticated_user_directory(client):
    login_res = client.post(
        "/api/v1/auth/login",
        json={"username": "chairman", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    response = client.get("/api/v1/users", headers=headers)

    assert response.status_code == 200
    assert {user["role"] for user in response.json()} == {"chairman", "student"}
    assert all("hashed_password" not in user for user in response.json())
    assert client.get("/api/v1/users").status_code == 401


def test_only_university_hierarchy_can_discard_meetings(client, test_db):
    chairman = test_db.query(User).filter_by(username="chairman").one()
    student = test_db.query(User).filter_by(username="aniket").one()
    room = test_db.query(Room).one()
    start_time = datetime(2026, 10, 20, 10, tzinfo=timezone.utc)
    end_time = start_time + timedelta(minutes=60)
    meeting = Meeting(
        title="Discard permission test",
        duration_minutes=60,
        start_time=start_time,
        end_time=end_time,
        organizer_id=student.id,
        room_id=room.id,
        status=MeetingStatus.ROOM_BOOKED,
    )
    test_db.add(meeting)
    test_db.commit()
    test_db.refresh(meeting)

    student_login = client.post(
        "/api/v1/auth/login",
        json={"username": "aniket", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    denied = client.post(
        f"/api/v1/meetings/{meeting.id}/discard", headers=student_headers, json={}
    )
    assert denied.status_code == 403

    chairman_login = client.post(
        "/api/v1/auth/login",
        json={"username": "chairman", "password": "password123"},
    )
    chairman_headers = {"Authorization": f"Bearer {chairman_login.json()['access_token']}"}
    discarded = client.post(
        f"/api/v1/meetings/{meeting.id}/discard", headers=chairman_headers, json={}
    )
    assert discarded.status_code == 200
    assert discarded.json()["status"] == "discarded"
    available_rooms = room_service.find_available_rooms(
        test_db, capacity_needed=2, start_time=start_time, end_time=end_time
    )
    assert room in available_rooms
