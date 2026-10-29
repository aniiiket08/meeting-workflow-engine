from datetime import datetime
from typing import Any

from app.services.calendar_service import calendar_service

# https://calendar.google.com/calendar/u/0/r
def fetch_attendee_freebusy(emails: list[str]) -> dict[str, Any]:
    """MCP tool: Fetch free/busy intervals for attendee emails."""
    raw_busy = calendar_service.get_busy_slots(emails)
    # Serialize datetime to ISO strings for MCP tool output
    serialized: dict[str, list[dict[str, str]]] = {}
    for email, slots in raw_busy.items():
        serialized[email] = [
            {"start": slot["start"].isoformat(), "end": slot["end"].isoformat(), "title": slot["title"]}
            for slot in slots
        ]
    return serialized
