"""Tests for room seeding, best-fit selection, availability API, and double-booking.

Covers:
  - seed_database idempotency: running twice produces exactly 4 named rooms, no duplicates
  - seed_database preserves existing user and room data on re-seed
  - RoomService.find_available_rooms: best-fit (smallest capacity that fits), equipment filter,
    capacity filter, double-booking conflict exclusion
  - run_room_booking_agent: auto best-fit path, explicit room_id path
  - run_room_booking_agent: double-booking raises Conflict
  - run_room_booking_agent: explicit room too small raises Conflict
  - GET /rooms/availability: returns correct status for each room, correct best_fit_id
  - GET /rooms/availability: booked room shown as "booked", too-small as "too_small"
"""

from datetime import datetime, timezone

import app.observability.tracer as tracer_module
import pytest
from app.agents.room_booking import run_room_booking_agent
from app.api.deps import get_db
from app.core.errors import Conflict, NotFound
from app.core.security import get_password_hash
from app.db.base import Base
from app.db.models.meeting import Meeting, MeetingStatus
from app.db.models.room import Room
from app.db.models.user import User, UserRole
from app.db.seed import seed_database
from app.main import app
from app.services.room_service import room_service
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# ── Shared in-memory DB ───────────────────────────────────────────────────────

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def db(monkeypatch_module):
    original = tracer_module.SessionLocal
    tracer_module.SessionLocal = TestingSessionLocal
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        tracer_module.SessionLocal = original


# monkeypatch_module fixture: pytest doesn't ship one, so we roll a minimal version
@pytest.fixture(scope="module")
def monkeypatch_module():
    """A module-scoped monkeypatch that undoes patches at module teardown."""
    patches: list = []

    class _MP:
        def setattr(self, obj, name, value):
            original = getattr(obj, name)
            setattr(obj, name, value)
            patches.append((obj, name, original))

    mp = _MP()
    yield mp
    for obj, name, original in reversed(patches):
        setattr(obj, name, original)


# ── Four canonical rooms (matching seed.py) ───────────────────────────────────

SEEDED_ROOMS = [
    {
        "name": "Auditorium",
        "capacity": 200,
        "equipment": ["projector", "mic", "whiteboard", "video_conf", "stage", "seating"],
    },
    {
        "name": "IoT Lab",
        "capacity": 40,
        "equipment": ["projector", "mic", "whiteboard", "stage"],
    },
    {
        "name": "STEP Hall",
        "capacity": 100,
        "equipment": ["projector", "mic", "whiteboard", "video_conf", "stage"],
    },
    {
        "name": "MB 104",
        "capacity": 60,
        "equipment": ["projector", "mic", "whiteboard", "stage"],
    },
]

# ── Isolated unit-test fixtures ───────────────────────────────────────────────

def _make_db():
    """Return a fresh in-memory session with schema only (no data)."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    Session = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    return Session()


def _seed_rooms(db) -> list[Room]:
    """Insert the 4 canonical rooms; return them ordered by capacity asc."""
    for spec in SEEDED_ROOMS:
        db.add(Room(name=spec["name"], capacity=spec["capacity"], equipment=spec["equipment"]))
    db.commit()
    return db.query(Room).order_by(Room.capacity.asc()).all()


def _make_user(db) -> User:
    u = User(
        name="Test Organiser",
        username="organiser",
        email="organiser@test.local",
        role=UserRole.HOD,
        hashed_password=get_password_hash("pw"),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_meeting(db, user: User, room: Room | None, start: datetime, end: datetime) -> Meeting:
    m = Meeting(
        title="Test Meeting",
        duration_minutes=int((end - start).total_seconds() // 60),
        organizer_id=user.id,
        room_id=room.id if room else None,
        start_time=start,
        end_time=end,
        status=MeetingStatus.ROOM_BOOKED,
    )
    db.add(m)
    db.commit()
    db.refresh(m)
    return m


# ─────────────────────────────────────────────────────────────────────────────
# 1. SEED IDEMPOTENCY
# ─────────────────────────────────────────────────────────────────────────────

class TestSeedIdempotency:
    def test_seed_creates_exactly_four_rooms(self, monkeypatch):
        db = _make_db()
        # Create a minimal user so seed_database doesn't fail on SEED_PASSWORD check
        from app.config import settings as _settings
        monkeypatch.setattr(_settings, "SEED_PASSWORD", "testpw")
        seed_database(db)
        rooms = db.query(Room).all()
        names = {r.name for r in rooms}
        assert names == {"Auditorium", "IoT Lab", "STEP Hall", "MB 104"}
        assert len(rooms) == 4
        db.close()

    def test_seed_is_idempotent_no_duplicates(self, monkeypatch):
        db = _make_db()
        from app.config import settings as _settings
        monkeypatch.setattr(_settings, "SEED_PASSWORD", "testpw")
        seed_database(db)
        seed_database(db)  # run twice
        assert db.query(Room).count() == 4
        db.close()

    def test_seed_preserves_existing_room_and_user_data(self, monkeypatch):
        db = _make_db()
        from app.config import settings as _settings
        monkeypatch.setattr(_settings, "SEED_PASSWORD", "testpw")
        seed_database(db)

        iot = db.query(Room).filter_by(name="IoT Lab").first()
        iot.capacity = 1
        iot.equipment = ["custom-equipment"]
        chairman = db.query(User).filter_by(username="chairman").first()
        chairman.name = "Customized Chairman"
        chairman.email = "custom-chairman@test.local"
        chairman.role = UserRole.TEACHER
        chairman.hashed_password = "existing-hash"
        db.commit()

        seed_database(db)
        iot_after = db.query(Room).filter_by(name="IoT Lab").first()
        chairman_after = db.query(User).filter_by(username="chairman").first()
        assert iot_after.capacity == 1
        assert iot_after.equipment == ["custom-equipment"]
        assert chairman_after.name == "Customized Chairman"
        assert chairman_after.email == "custom-chairman@test.local"
        assert chairman_after.role == UserRole.TEACHER
        assert chairman_after.hashed_password == "existing-hash"
        db.close()

    def test_seed_does_not_rename_legacy_student(self, monkeypatch):
        db = _make_db()
        from app.config import settings as _settings

        monkeypatch.setattr(_settings, "SEED_PASSWORD", "testpw")
        legacy = User(
            name="Legacy Student",
            username="student",
            email="legacy-student@test.local",
            role=UserRole.STUDENT,
            hashed_password="existing-hash",
        )
        db.add(legacy)
        db.commit()

        seed_database(db)

        db.refresh(legacy)
        assert legacy.username == "student"
        assert legacy.email == "legacy-student@test.local"
        assert legacy.hashed_password == "existing-hash"
        assert db.query(User).filter_by(username="aniket").count() == 1
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 2. BEST-FIT SELECTION  (find_available_rooms + min capacity logic)
# ─────────────────────────────────────────────────────────────────────────────

class TestBestFitSelection:
    """Best fit = smallest room whose capacity ≥ headcount AND has all required equipment."""

    START = datetime(2026, 11, 3, 9, 0, tzinfo=timezone.utc)
    END   = datetime(2026, 11, 3, 10, 0, tzinfo=timezone.utc)

    def test_best_fit_is_smallest_room_that_fits_headcount(self):
        db = _make_db()
        _seed_rooms(db)
        # headcount = 45 → IoT Lab (40) too small; STEP Hall (100) fits; MB 104 (60) fits
        # best fit = MB 104 (60, smallest ≥ 45)
        available = room_service.find_available_rooms(
            db, capacity_needed=45,
            start_time=self.START, end_time=self.END,
        )
        assert len(available) >= 2
        best = min(available, key=lambda r: r.capacity)
        assert best.name == "MB 104"
        db.close()

    def test_best_fit_excludes_rooms_missing_required_equipment(self):
        db = _make_db()
        _seed_rooms(db)
        # video_conf leaves STEP Hall (100) and Auditorium (200) as the available rooms.
        available = room_service.find_available_rooms(
            db, capacity_needed=1,
            start_time=self.START, end_time=self.END,
            required_equipment=["video_conf"],
        )
        names = {r.name for r in available}
        assert names == {"STEP Hall", "Auditorium"}
        best = min(available, key=lambda r: r.capacity)
        assert best.name == "STEP Hall"
        db.close()

    def test_best_fit_excludes_rooms_too_small(self):
        db = _make_db()
        _seed_rooms(db)
        # headcount = 150 → only Auditorium (200) fits
        available = room_service.find_available_rooms(
            db, capacity_needed=150,
            start_time=self.START, end_time=self.END,
        )
        assert len(available) == 1
        assert available[0].name == "Auditorium"
        db.close()

    def test_no_room_available_returns_empty_list(self):
        db = _make_db()
        _seed_rooms(db)
        # headcount = 201 → no room fits
        available = room_service.find_available_rooms(
            db, capacity_needed=201,
            start_time=self.START, end_time=self.END,
        )
        assert available == []
        db.close()

    def test_best_fit_skips_booked_room(self):
        db = _make_db()
        rooms = _seed_rooms(db)
        user = _make_user(db)
        # Book MB 104 (capacity 60) for the slot
        mb104 = next(r for r in rooms if r.name == "MB 104")
        _make_meeting(db, user, mb104, self.START, self.END)
        # headcount = 45 → MB 104 booked; next smallest that fits = STEP Hall (100)
        available = room_service.find_available_rooms(
            db, capacity_needed=45,
            start_time=self.START, end_time=self.END,
        )
        names = {r.name for r in available}
        assert "MB 104" not in names
        assert "STEP Hall" in names or "Auditorium" in names
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 3. DOUBLE-BOOKING REJECTION
# ─────────────────────────────────────────────────────────────────────────────

class TestDoubleBookingRejection:
    START = datetime(2026, 11, 4, 10, 0, tzinfo=timezone.utc)
    END   = datetime(2026, 11, 4, 11, 0, tzinfo=timezone.utc)

    def test_booking_same_room_twice_raises_conflict(self):
        db = _make_db()
        rooms = _seed_rooms(db)
        user = _make_user(db)
        # Create a fresh unbooked meeting
        iot_lab = next(r for r in rooms if r.name == "IoT Lab")
        m1 = Meeting(
            title="First booking",
            duration_minutes=60,
            organizer_id=user.id,
            status=MeetingStatus.REQUESTED,
        )
        db.add(m1)
        db.commit()
        db.refresh(m1)
        # Book IoT Lab for m1
        room_service.book_room(db, m1.id, iot_lab.id, self.START, self.END)

        # Now try to book the same room for a second meeting at the same time
        m2 = Meeting(
            title="Second (conflicting) booking",
            duration_minutes=60,
            organizer_id=user.id,
            status=MeetingStatus.REQUESTED,
        )
        db.add(m2)
        db.commit()
        db.refresh(m2)

        with pytest.raises(Conflict, match="already booked"):
            room_service.book_room(db, m2.id, iot_lab.id, self.START, self.END)
        db.close()

    def test_room_booking_agent_raises_conflict_on_double_booking(self, monkeypatch):
        """run_room_booking_agent should raise Conflict when all suitable rooms
        for the headcount are already booked."""
        db = _make_db()
        rooms = _seed_rooms(db)
        user = _make_user(db)

        # For headcount=50, rooms that fit: MB 104 (60), STEP Hall (100), Auditorium (200).
        # Book all three of them, so no room is available.
        mb_104 = next(r for r in rooms if r.name == "MB 104")
        step_hall = next(r for r in rooms if r.name == "STEP Hall")
        auditorium = next(r for r in rooms if r.name == "Auditorium")
        
        for i, room in enumerate([mb_104, step_hall, auditorium], 1):
            blocker = Meeting(
                title=f"Blocker {i}",
                duration_minutes=60,
                organizer_id=user.id,
                status=MeetingStatus.REQUESTED,
            )
            db.add(blocker)
            db.commit()
            db.refresh(blocker)
            room_service.book_room(db, blocker.id, room.id, self.START, self.END)

        # Fourth meeting: headcount=50 → needs one of the three booked rooms.
        # Agent should raise Conflict because no suitable room is available.
        target = Meeting(
            title="Target meeting",
            duration_minutes=60,
            organizer_id=user.id,
            status=MeetingStatus.REQUESTED,
        )
        db.add(target)
        db.commit()
        db.refresh(target)

        with pytest.raises(Conflict):
            run_room_booking_agent(
                db=db,
                meeting_id=target.id,
                headcount=50,
                start_time_iso=self.START.isoformat(),
                end_time_iso=self.END.isoformat(),
                equipment_needed=None,
            )
        db.close()

    def test_room_booking_agent_explicit_room_too_small_raises_conflict(self):
        db = _make_db()
        rooms = _seed_rooms(db)
        user = _make_user(db)
        m = Meeting(
            title="Too-small test",
            duration_minutes=60,
            organizer_id=user.id,
            status=MeetingStatus.REQUESTED,
        )
        db.add(m)
        db.commit()
        db.refresh(m)
        iot_lab = next(r for r in rooms if r.name == "IoT Lab")  # capacity 40
        with pytest.raises(Conflict, match="seats"):
            run_room_booking_agent(
                db=db,
                meeting_id=m.id,
                headcount=50,          # exceeds IoT Lab capacity
                start_time_iso=self.START.isoformat(),
                end_time_iso=self.END.isoformat(),
                room_id=iot_lab.id,    # explicit room too small
            )
        db.close()

    def test_room_booking_agent_explicit_nonexistent_room_raises_not_found(self):
        db = _make_db()
        _seed_rooms(db)
        user = _make_user(db)
        m = Meeting(
            title="Ghost room test",
            duration_minutes=60,
            organizer_id=user.id,
            status=MeetingStatus.REQUESTED,
        )
        db.add(m)
        db.commit()
        db.refresh(m)
        with pytest.raises(NotFound):
            run_room_booking_agent(
                db=db,
                meeting_id=m.id,
                headcount=1,
                start_time_iso=self.START.isoformat(),
                end_time_iso=self.END.isoformat(),
                room_id=99999,
            )
        db.close()


# ─────────────────────────────────────────────────────────────────────────────
# 4. /rooms/availability API ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def avail_db():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    Sess = sessionmaker(autocommit=False, autoflush=False, bind=eng)
    session = Sess()
    # Seed rooms + one user
    for spec in SEEDED_ROOMS:
        session.add(Room(name=spec["name"], capacity=spec["capacity"], equipment=spec["equipment"]))
    hashed = get_password_hash("pw")
    session.add(
        User(
            name="Chair",
            username="chair_avail",
            email="chair_avail@test.local",
            role=UserRole.CHAIRMAN,
            hashed_password=hashed,
        )
    )
    session.commit()
    return session


@pytest.fixture(scope="module")
def avail_client(avail_db):
    original = tracer_module.SessionLocal
    tracer_module.SessionLocal = TestingSessionLocal  # doesn't matter — no tracing in GET /rooms
    app.dependency_overrides[get_db] = lambda: avail_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    tracer_module.SessionLocal = original


def _auth_headers(client: TestClient, username: str = "chair_avail", password: str = "pw") -> dict:
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed: {res.text}"
    return {"Authorization": f"Bearer {res.json()['access_token']}"}


START_ISO = "2026-11-10T09:00:00+00:00"
END_ISO   = "2026-11-10T10:00:00+00:00"


class TestRoomAvailabilityEndpoint:
    def test_all_rooms_available_when_no_bookings(self, avail_client):
        headers = _auth_headers(avail_client)
        res = avail_client.get(
            f"/api/v1/rooms/availability?start_time={START_ISO}&end_time={END_ISO}&headcount=1",
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert "rooms" in data
        statuses = {r["name"]: r["status"] for r in data["rooms"]}
        # All 4 rooms seat ≥ 1, none booked
        assert all(s == "available" for s in statuses.values()), statuses

    def test_best_fit_is_smallest_for_given_headcount(self, avail_client):
        headers = _auth_headers(avail_client)
        # headcount = 45 → IoT Lab (40) too small; MB 104 (60) is best fit
        res = avail_client.get(
            f"/api/v1/rooms/availability?start_time={START_ISO}&end_time={END_ISO}&headcount=45",
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["best_fit_id"] is not None
        best = next(r for r in data["rooms"] if r["id"] == data["best_fit_id"])
        assert best["name"] == "MB 104"
        assert best["is_best_fit"] is True
        assert "best_fit_reason" in best

    def test_too_small_rooms_marked_correctly(self, avail_client):
        headers = _auth_headers(avail_client)
        res = avail_client.get(
            f"/api/v1/rooms/availability?start_time={START_ISO}&end_time={END_ISO}&headcount=80",
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        room_map = {r["name"]: r for r in data["rooms"]}
        # IoT Lab (40) and MB 104 (60) are too small for 80
        assert room_map["IoT Lab"]["status"] == "too_small"
        assert room_map["MB 104"]["status"] == "too_small"
        # STEP Hall (100) and Auditorium (200) fit
        assert room_map["STEP Hall"]["status"] == "available"
        assert room_map["Auditorium"]["status"] == "available"

    def test_booked_room_shown_as_booked(self, avail_client, avail_db):
        # Book STEP Hall for the slot directly
        step = avail_db.query(Room).filter_by(name="STEP Hall").first()
        user = avail_db.query(User).filter_by(username="chair_avail").first()
        booking_meeting = Meeting(
            title="Block STEP Hall",
            duration_minutes=60,
            organizer_id=user.id,
            room_id=step.id,
            start_time=datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 11, 10, 10, 0, tzinfo=timezone.utc),
            status=MeetingStatus.ROOM_BOOKED,
        )
        avail_db.add(booking_meeting)
        avail_db.commit()

        headers = _auth_headers(avail_client)
        res = avail_client.get(
            f"/api/v1/rooms/availability?start_time={START_ISO}&end_time={END_ISO}&headcount=1",
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        step_entry = next(r for r in data["rooms"] if r["name"] == "STEP Hall")
        assert step_entry["status"] == "booked"
        assert step_entry["reason"] != ""

    def test_equipment_filter_excludes_missing_rooms(self, avail_client):
        headers = _auth_headers(avail_client)
        # Require video_conf → IoT Lab and MB 104 lack it
        res = avail_client.get(
            f"/api/v1/rooms/availability?start_time={START_ISO}&end_time={END_ISO}"
            f"&headcount=1&equipment=video_conf",
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        room_map = {r["name"]: r for r in data["rooms"]}
        assert room_map["IoT Lab"]["status"] == "too_small"
        assert room_map["MB 104"]["status"] == "too_small"
        # Auditorium and STEP Hall have video_conf
        avail_statuses = [
            r["status"] for r in data["rooms"]
            if r["name"] in ("Auditorium", "STEP Hall")
        ]
        # STEP Hall may be booked from the previous test — check at least one is available
        assert any(s == "available" for s in avail_statuses)

    def test_requires_authentication(self, avail_client):
        res = avail_client.get(
            f"/api/v1/rooms/availability?start_time={START_ISO}&end_time={END_ISO}&headcount=1"
        )
        assert res.status_code == 401
