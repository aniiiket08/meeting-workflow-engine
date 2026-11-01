"""
Phase 2 — Database Query Latency Benchmark
Tests SQLite query patterns, N+1 risks, transaction latency.
"""
import json
import statistics
import sys
import time

sys.path.insert(0, "backend")

from sqlalchemy import text
from app.db.session import SessionLocal
from app.db.models.meeting import Meeting, Attendee, MeetingStatus
from app.db.models.room import Room
from app.db.models.user import User
from app.db.models.minutes import Minutes
from app.db.models.agenda import Agenda, Decision
from app.db.models.action import ActionItem

results: dict = {}


def bench(label: str, fn, n: int = 50) -> dict:
    latencies = []
    errors = 0
    for _ in range(n):
        t0 = time.perf_counter()
        try:
            fn()
        except Exception:
            errors += 1
        latencies.append((time.perf_counter() - t0) * 1000)
    s = sorted(latencies)
    rec = {
        "p50_ms": round(statistics.median(s), 3),
        "p90_ms": round(s[int(len(s) * 0.9)], 3),
        "p99_ms": round(s[int(len(s) * 0.99)], 3) if len(s) >= 100 else round(s[-1], 3),
        "min_ms": round(min(s), 3),
        "max_ms": round(max(s), 3),
        "mean_ms": round(statistics.mean(s), 3),
        "errors": errors,
        "n": n,
    }
    results[label] = rec
    print(f"{label}: p50={rec['p50_ms']}ms  p90={rec['p90_ms']}ms  min={rec['min_ms']}ms  max={rec['max_ms']}ms  err={errors}")
    return rec


# ── Single-record queries ────────────────────────────────────────────────────
print("=== Database Query Benchmarks ===")

with SessionLocal() as db:
    all_users = db.query(User).all()
    user_ids = [u.id for u in all_users]
    all_rooms = db.query(Room).all()
    room_ids = [r.id for r in all_rooms]

import itertools
uid_cycle = itertools.cycle(user_ids) if user_ids else iter([1])
rid_cycle = itertools.cycle(room_ids) if room_ids else iter([1])


def q_user_by_id():
    with SessionLocal() as db:
        uid = next(uid_cycle)
        db.query(User).filter(User.id == uid).first()


def q_user_by_email():
    with SessionLocal() as db:
        db.query(User).filter(User.email == "chairman@university.com").first()


def q_all_rooms():
    with SessionLocal() as db:
        db.query(Room).all()


def q_all_meetings():
    with SessionLocal() as db:
        db.query(Meeting).all()


def q_meetings_with_attendees():
    """Simulates potential N+1: fetch all meetings then iterate attendees."""
    with SessionLocal() as db:
        meetings = db.query(Meeting).limit(20).all()
        # Simulate accessing attendees per meeting
        for m in meetings:
            _ = m.attendees


def q_minutes_latest():
    with SessionLocal() as db:
        db.query(Minutes).order_by(Minutes.version.desc()).first()


def q_actions_all():
    with SessionLocal() as db:
        db.query(ActionItem).all()


def q_raw_sqlite_ping():
    with SessionLocal() as db:
        db.execute(text("SELECT 1")).fetchone()


bench("SELECT 1 (connection overhead)", q_raw_sqlite_ping, n=100)
bench("User by id", q_user_by_id, n=100)
bench("User by email", q_user_by_email, n=100)
bench("All rooms (4 rows)", q_all_rooms, n=100)
bench("All meetings (0 rows)", q_all_meetings, n=100)
bench("Meetings + attendees access", q_meetings_with_attendees, n=50)
bench("Minutes latest version", q_minutes_latest, n=100)
bench("All actions", q_actions_all, n=100)

# ── Insert + rollback latency (measures write overhead) ─────────────────────
def q_insert_rollback():
    with SessionLocal() as db:
        m = Meeting(
            title="[BENCH] Ephemeral",
            organizer_id=user_ids[0] if user_ids else 1,
            duration_minutes=30,
            status=MeetingStatus.REQUESTED,
        )
        db.add(m)
        db.flush()
        db.rollback()

bench("Meeting INSERT + rollback", q_insert_rollback, n=50)

# ── Connection pool info ─────────────────────────────────────────────────────
from app.db.session import engine
pool = engine.pool
pool_info = {
    "pool_class": type(pool).__name__,
    "pool_size": getattr(pool, '_pool', None) and getattr(pool, '_pool', None).maxsize,
    "overflow": getattr(pool, '_overflow', None),
}
print("\nPool info:", pool_info)

print()
print("=" * 55)
print("DATABASE BENCHMARK RESULTS (JSON)")
print("=" * 55)
print(json.dumps(results, indent=2))

with open("evaluation/baseline_db.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved -> evaluation/baseline_db.json")

