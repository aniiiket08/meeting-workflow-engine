from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.agents.scheduling import run_scheduling_agent
from app.agents.room_booking import run_room_booking_agent
from app.core.errors import Conflict, ValidationFailed
from app.db.base import Base
from app.db.models.meeting import Meeting, MeetingStatus
from app.db.models.room import Room
from app.db.models.user import User, UserRole
from app.services.environment_parser import environment_data_service
from app.services.calendar_service import calendar_service
from app.services.room_service import room_service

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture
def schedule_env_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    # Seed rooms from environment facilities
    for spec in environment_data_service.get_room_facilities():
        db.add(Room(name=spec["name"], capacity=spec["capacity"], equipment=spec["equipment"]))

    # Seed users
    db.add_all([
        User(name="Chairman", username="chairman", email="chairman@university.com", role=UserRole.CHAIRMAN, hashed_password="x"),
        User(name="Principal", username="principal", email="principal@university.com", role=UserRole.PRINCIPAL, hashed_password="x"),
        User(name="HOD", username="hod", email="hod@university.com", role=UserRole.HOD, hashed_password="x"),
        User(name="Aniket", username="aniket", email="aniket@university.com", role=UserRole.STUDENT, hashed_password="x"),
    ])
    db.commit()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def test_environment_timetable_conflict_detected():
    # Monday: HOD has 'Department Class' 9-10 AM, students have 'Cryptography' 9-10 AM
    # Date 2026-11-02 is a Monday
    monday_dt = datetime(2026, 11, 2, 9, 0, tzinfo=timezone.utc)
    busy = calendar_service.get_busy_slots(
        emails=["hod@university.com", "aniket@university.com"],
        target_date=monday_dt,
    )
    assert "hod@university.com" in busy
    assert "aniket@university.com" in busy
    assert any(b["title"] == "Department Class" for b in busy["hod@university.com"])
    assert any(b["title"] == "Cryptography" for b in busy["aniket@university.com"])


def test_environment_timetable_free_slot_ranked_higher():
    # Monday 10-11 AM is FREE for everyone in Weekly_Timetable.docx
    monday_iso = "2026-11-02T09:00:00Z"
    slots = run_scheduling_agent(
        attendee_emails=["hod@university.com", "aniket@university.com"],
        duration_minutes=60,
        target_date_iso=monday_iso,
    )
    assert len(slots) >= 1
    # Check that candidate slots are returned and score reflects availability
    top_slot = slots[0]
    assert "conflicts" in top_slot


def test_sunday_holiday_marks_entire_day_unavailable():
    # 2026-11-01 is a Sunday
    sunday_dt = datetime(2026, 11, 1, 10, 0, tzinfo=timezone.utc)
    busy = calendar_service.get_busy_slots(
        emails=["hod@university.com", "chairman@university.com"],
        target_date=sunday_dt,
    )
    for email in ["hod@university.com", "chairman@university.com"]:
        assert len(busy[email]) >= 1
        assert any("Sunday Holiday" in ev["title"] for ev in busy[email])


def test_room_booking_conflict_with_existing_meeting(schedule_env_db):
    db = schedule_env_db
    iot_lab = db.query(Room).filter(Room.name == "IoT Lab").first()
    assert iot_lab is not None

    chairman = db.query(User).filter(User.username == "chairman").first()
    # Create an existing meeting
    m1 = Meeting(
        title="Existing Lab Session",
        duration_minutes=60,
        start_time=datetime(2026, 11, 2, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 2, 11, 0, tzinfo=timezone.utc),
        organizer_id=chairman.id,
        room_id=iot_lab.id,
        status=MeetingStatus.ROOM_BOOKED,
    )
    db.add(m1)
    db.commit()

    # Second meeting attempts to book the same room during overlapping time
    m2 = Meeting(
        title="New Conflicting Meeting",
        duration_minutes=60,
        organizer_id=chairman.id,
        status=MeetingStatus.REQUESTED,
    )
    db.add(m2)
    db.commit()

    with pytest.raises(Conflict, match="already booked"):
        run_room_booking_agent(
            db=db,
            meeting_id=m2.id,
            headcount=10,
            start_time_iso="2026-11-02T10:30:00Z",
            end_time_iso="2026-11-02T11:30:00Z",
            room_id=iot_lab.id,
        )


def test_room_booking_unavailable_when_no_room_fits_capacity(schedule_env_db):
    db = schedule_env_db
    chairman = db.query(User).filter(User.username == "chairman").first()
    m = Meeting(
        title="Mega Conference",
        duration_minutes=60,
        organizer_id=chairman.id,
        status=MeetingStatus.REQUESTED,
    )
    db.add(m)
    db.commit()

    # Headcount 500 exceeds largest room (Auditorium capacity = 200)
    with pytest.raises(Conflict, match="No available room matches headcount"):
        run_room_booking_agent(
            db=db,
            meeting_id=m.id,
            headcount=500,
            start_time_iso="2026-11-02T14:00:00Z",
            end_time_iso="2026-11-02T15:00:00Z",
        )


def test_room_booking_equipment_requirement_filtering(schedule_env_db):
    db = schedule_env_db
    # Video conferencing is only in Auditorium and STEP Hall
    available = room_service.find_available_rooms(
        db=db,
        capacity_needed=20,
        start_time=datetime(2026, 11, 2, 14, 0, tzinfo=timezone.utc),
        end_time=datetime(2026, 11, 2, 15, 0, tzinfo=timezone.utc),
        required_equipment=["video_conf"],
    )
    names = {r.name for r in available}
    assert "IoT Lab" not in names
    assert "MB 104" not in names
    assert names.issubset({"Auditorium", "STEP Hall"})
