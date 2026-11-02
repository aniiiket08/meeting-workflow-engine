"""Standard MCP stdio server for local MCP clients."""

import sys
from contextlib import redirect_stdout
from typing import Any

from mcp.server.mcpserver import MCPServer

with redirect_stdout(sys.stderr):
    from mcp_server.server import mcp_server as tool_registry

protocol_server = MCPServer(
    name="meeting-organizer-agent",
    version="0.1.0",
    instructions="Meeting scheduling, room booking, calendar, and Zoom tools.",
)


def calendar_freebusy(emails: list[str]) -> dict[str, Any]:
    """Fetch free/busy intervals for attendee email addresses."""
    return tool_registry.call_tool(
        "calendar_freebusy",
        {"emails": emails},
        agent_name="orchestrator",
    )


def room_search(
    capacity_needed: int = 1,
    start_time: str | None = None,
    end_time: str | None = None,
    required_equipment: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Search available rooms for the requested time and equipment."""
    return tool_registry.call_tool(
        "room_search",
        {
            "capacity_needed": capacity_needed,
            "start_time": start_time,
            "end_time": end_time,
            "required_equipment": required_equipment,
        },
        agent_name="orchestrator",
    )


def room_book(
    meeting_id: int,
    room_id: int,
    start_time: str,
    end_time: str,
) -> dict[str, Any]:
    """Book a room for an existing meeting."""
    return tool_registry.call_tool(
        "room_book",
        {
            "meeting_id": meeting_id,
            "room_id": room_id,
            "start_time": start_time,
            "end_time": end_time,
        },
        agent_name="orchestrator",
    )


def zoom_create_meeting(
    topic: str,
    start_time: str,
    duration_minutes: int = 60,
    timezone: str = "UTC",
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Create an online meeting using configured Zoom credentials or mock mode."""
    return tool_registry.call_tool(
        "zoom_create_meeting",
        {
            "topic": topic,
            "start_time": start_time,
            "duration_minutes": duration_minutes,
            "timezone": timezone,
            "idempotency_key": idempotency_key,
        },
        agent_name="orchestrator",
    )


def zoom_get_meeting(meeting_id: str) -> dict[str, Any]:
    """Retrieve an online meeting by ID."""
    return tool_registry.call_tool(
        "zoom_get_meeting",
        {"meeting_id": meeting_id},
        agent_name="orchestrator",
    )


protocol_server.add_tool(calendar_freebusy, description="Fetch attendee busy intervals")
protocol_server.add_tool(
    room_search,
    description="Search available rooms matching capacity, window, and equipment",
)
protocol_server.add_tool(
    room_book,
    description="Book a room for a meeting with double-booking prevention",
)
protocol_server.add_tool(
    zoom_create_meeting,
    description="Create a Zoom meeting with topic, start time, duration, and timezone",
)
protocol_server.add_tool(
    zoom_get_meeting,
    description="Retrieve Zoom meeting details by meeting ID",
)


def main() -> None:
    protocol_server.run(transport="stdio")


if __name__ == "__main__":
    main()
