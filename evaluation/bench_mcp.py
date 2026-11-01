"""
Phase 2 & 4 — MCP Tool Latency and Correctness Benchmark
Tests room_search and room_book with safe, non-destructive scenarios.
"""
import json
import statistics
import sys
import time

sys.path.insert(0, "backend")

from mcp_server.tools.room_tools import room_book, room_search

RESULTS: dict = {}

# ── room_search ──────────────────────────────────────────────────────────────
print("=== MCP: room_search ===")

search_cases = [
    # (label, capacity, start, end, expect_results)
    ("small room 10 pax", 10, "2026-11-05T10:00:00", "2026-11-05T11:00:00", True),
    ("large room 150 pax", 150, "2026-11-05T10:00:00", "2026-11-05T11:00:00", True),
    ("oversized 500 pax", 500, "2026-11-05T10:00:00", "2026-11-05T11:00:00", False),
    ("no time window (should fail)", 10, None, None, False),
]

search_latencies = []
search_passed = 0
for label, cap, start, end, expect in search_cases:
    t0 = time.perf_counter()
    try:
        if start is None or end is None:
            # Expect ValidationFailed
            from app.core.errors import ValidationFailed
            try:
                room_search(capacity_needed=cap, start_time=start, end_time=end)
                status = "FAIL (expected error but got result)"
            except ValidationFailed as ve:
                status = f"OK (correctly raised ValidationFailed)"
                elapsed = (time.perf_counter() - t0) * 1000
                search_latencies.append(elapsed)
                if not expect:
                    search_passed += 1
                print(f"  [{label}]: {status} | {elapsed:.2f}ms")
                RESULTS[f"room_search:{label}"] = {"status": "ok", "latency_ms": round(elapsed, 2)}
                continue
        else:
            rooms = room_search(capacity_needed=cap, start_time=start, end_time=end)
            elapsed = (time.perf_counter() - t0) * 1000
            got_results = len(rooms) > 0
            status = "OK" if got_results == expect else f"FAIL (got {len(rooms)} rooms, expect_results={expect})"
            if got_results == expect:
                search_passed += 1
    except Exception as exc:
        elapsed = (time.perf_counter() - t0) * 1000
        rooms = []
        status = f"EXCEPTION: {type(exc).__name__}: {str(exc)[:60]}"

    search_latencies.append(elapsed)
    room_names = [r["name"] for r in rooms] if isinstance(rooms, list) else []
    print(f"  [{label}]: {status} | {elapsed:.2f}ms | rooms={room_names}")
    RESULTS[f"room_search:{label}"] = {
        "status": "ok" if "OK" in status else "fail",
        "latency_ms": round(elapsed, 2),
        "rooms_returned": room_names,
    }

print(f"\nroom_search: {search_passed}/{len(search_cases)} cases passed")
print(f"room_search latencies (ms): {[round(l,2) for l in search_latencies]}")
if search_latencies:
    print(f"  mean={statistics.mean(search_latencies):.2f}ms  min={min(search_latencies):.2f}ms  max={max(search_latencies):.2f}ms")

# ── room_book (safe: use a test meeting_id that won't conflict) ──────────────
print("\n=== MCP: room_book ===")

# Create a test meeting row
from sqlalchemy import text
from app.db.session import SessionLocal
from app.db.models.meeting import Meeting, MeetingStatus
from app.db.models.user import User

with SessionLocal() as db:
    organizer = db.query(User).first()
    test_meeting = Meeting(
        title="[TEST] Room Booking Eval",
        organizer_id=organizer.id,
        duration_minutes=60,
        status=MeetingStatus.REQUESTED,
    )
    db.add(test_meeting)
    db.commit()
    db.refresh(test_meeting)
    TEST_MEETING_ID = test_meeting.id
    print(f"Created test meeting id={TEST_MEETING_ID}")

    # Get a valid room id
    rooms = room_search(capacity_needed=10, start_time="2026-11-10T14:00:00", end_time="2026-11-10T15:00:00")
    if rooms:
        ROOM_ID = rooms[0]["id"]
        print(f"Booking room_id={ROOM_ID} ({rooms[0]['name']}) for test meeting")

        # First booking — should succeed
        t0 = time.perf_counter()
        try:
            booking = room_book(
                meeting_id=TEST_MEETING_ID,
                room_id=ROOM_ID,
                start_time="2026-11-10T14:00:00",
                end_time="2026-11-10T15:00:00",
            )
            elapsed = (time.perf_counter() - t0) * 1000
            print(f"  First booking: status={booking.get('status')} | {elapsed:.2f}ms")
            RESULTS["room_book:first"] = {"status": booking.get("status"), "latency_ms": round(elapsed, 2)}
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            print(f"  First booking FAILED: {exc} | {elapsed:.2f}ms")
            RESULTS["room_book:first"] = {"status": "error", "error": str(exc), "latency_ms": round(elapsed, 2)}

        # Double-booking — should be prevented
        with SessionLocal() as db2:
            test_meeting2 = Meeting(
                title="[TEST] Room Booking Eval 2",
                organizer_id=organizer.id,
                duration_minutes=60,
                status=MeetingStatus.REQUESTED,
            )
            db2.add(test_meeting2)
            db2.commit()
            db2.refresh(test_meeting2)
            TEST_MEETING_ID2 = test_meeting2.id

        t0 = time.perf_counter()
        try:
            booking2 = room_book(
                meeting_id=TEST_MEETING_ID2,
                room_id=ROOM_ID,
                start_time="2026-11-10T14:30:00",
                end_time="2026-11-10T15:30:00",
            )
            elapsed = (time.perf_counter() - t0) * 1000
            print(f"  Double-booking: status={booking2.get('status')} (should have been rejected) | {elapsed:.2f}ms")
            RESULTS["room_book:double_booking_prevention"] = {
                "status": "FAIL - double booking was allowed",
                "latency_ms": round(elapsed, 2),
            }
        except Exception as exc:
            elapsed = (time.perf_counter() - t0) * 1000
            print(f"  Double-booking correctly rejected: {type(exc).__name__}: {str(exc)[:80]} | {elapsed:.2f}ms")
            RESULTS["room_book:double_booking_prevention"] = {
                "status": "ok - correctly rejected",
                "error_type": type(exc).__name__,
                "latency_ms": round(elapsed, 2),
            }

        # Clean up test meetings
        with SessionLocal() as db_clean:
            for mid in [TEST_MEETING_ID, TEST_MEETING_ID2]:
                m = db_clean.query(Meeting).filter(Meeting.id == mid).first()
                if m:
                    db_clean.delete(m)
            db_clean.commit()
        print("  Cleaned up test meetings")

print()
print("=" * 55)
print("MCP TOOL RESULTS (JSON)")
print("=" * 55)
print(json.dumps(RESULTS, indent=2))

with open("evaluation/baseline_mcp.json", "w") as f:
    json.dump(RESULTS, f, indent=2)
print("\nSaved -> evaluation/baseline_mcp.json")

