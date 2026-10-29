from datetime import datetime
from typing import Any
from sqlalchemy.orm import Session
from dateutil.parser import parse as parse_date

from app.core.errors import ValidationFailed
from app.db.session import SessionLocal
from app.services.room_service import room_service


def room_search(
    capacity_needed: int = 1,
    start_time: str | None = None,
    end_time: str | None = None,
    required_equipment: list[str] | None = None,
    db: Session | None = None,
) -> list[dict[str, Any]]:
    """MCP tool: Search available rooms matching capacity, window, and equipment."""
    if start_time is None or end_time is None:
        raise ValidationFailed("start_time and end_time are required to search available rooms.")

    start_dt = parse_date(start_time)
    end_dt = parse_date(end_time)

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        rooms = room_service.find_available_rooms(
            db=db,
            capacity_needed=capacity_needed,
            start_time=start_dt,
            end_time=end_dt,
            required_equipment=required_equipment,
        )
        return [
            {
                "id": r.id,
                "name": r.name,
                "capacity": r.capacity,
                "equipment": r.equipment,
            }
            for r in rooms
        ]
    finally:
        if close_session:
            db.close()


def room_book(
    meeting_id: int,
    room_id: int,
    start_time: str,
    end_time: str,
    db: Session | None = None,
) -> dict[str, Any]:
    """MCP tool: Book a room for a meeting with double-booking prevention."""
    start_dt = parse_date(start_time)
    end_dt = parse_date(end_time)

    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        room = room_service.book_room(
            db=db,
            meeting_id=meeting_id,
            room_id=room_id,
            start_time=start_dt,
            end_time=end_dt,
        )
        return {
            "status": "booked",
            "room_id": room.id,
            "room_name": room.name,
            "meeting_id": meeting_id,
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
        }
    finally:
        if close_session:
            db.close()
