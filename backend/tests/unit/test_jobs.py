from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.db.models
import app.services.job_worker as job_worker
from app.db.base import Base
from app.db.models.job import Job
from app.db.models.meeting import Meeting
from app.db.models.user import User, UserRole


def _session_factory():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(autoflush=False, bind=engine)
    db = factory()
    db.add(
        User(
            name="Job Owner",
            username="job-owner",
            email="job-owner@example.test",
            role=UserRole.CHAIRMAN,
            hashed_password="unused",
        )
    )
    db.commit()
    owner = db.query(User).one()
    meeting = Meeting(title="Job test", organizer_id=owner.id)
    db.add(meeting)
    db.commit()
    return engine, factory, db, owner.id, meeting.id


def test_enqueue_deduplicates_an_active_job():
    engine, _, db, owner_id, meeting_id = _session_factory()
    try:
        first = job_worker.enqueue_job(
            db, "agenda_generate", owner_id, {}, "Drafting agenda...", meeting_id=meeting_id
        )
        second = job_worker.enqueue_job(
            db, "agenda_generate", owner_id, {"ignored": True}, "Drafting agenda...", meeting_id=meeting_id
        )
        assert first.id == second.id
        assert db.query(Job).count() == 1
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_worker_completes_and_persists_result(monkeypatch):
    engine, factory, db, owner_id, _ = _session_factory()
    try:
        job = job_worker.enqueue_job(db, "test_success", owner_id, {"retained": True}, "Working...")
        monkeypatch.setattr(job_worker, "SessionLocal", factory)
        monkeypatch.setattr(job_worker, "_process", lambda _job, _db: {"ok": True})

        assert job_worker._run_one()
        db.expire_all()
        completed = db.query(Job).filter(Job.id == job.id).one()
        assert completed.status == "completed"
        assert completed.result_json == {"ok": True}
        assert completed.payload_json is None
        assert completed.attempts == 1
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_worker_retries_then_records_a_clear_failure(monkeypatch):
    engine, factory, db, owner_id, _ = _session_factory()
    try:
        job = job_worker.enqueue_job(db, "test_failure", owner_id, {}, "Working...")
        monkeypatch.setattr(job_worker, "SessionLocal", factory)

        def fail(_job, _db):
            raise ValueError("provider unavailable")

        monkeypatch.setattr(job_worker, "_process", fail)
        for expected_attempt in range(1, job_worker._MAX_ATTEMPTS + 1):
            assert job_worker._run_one()
            db.expire_all()
            failed = db.query(Job).filter(Job.id == job.id).one()
            assert failed.attempts == expected_attempt
        assert failed.status == "failed"
        assert failed.error == "ValueError: provider unavailable"
        assert failed.progress_text == "Failed"
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
