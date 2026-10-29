import json
from typing import Any
from app.core.errors import ToolError
from app.core.logging import setup_logging
from mcp_server.tools.calendar_tools import fetch_attendee_freebusy
from mcp_server.tools.room_tools import room_book, room_search
from mcp_server.tools.zoom_tools import zoom_create_meeting, zoom_get_meeting

logger = setup_logging()


class MCPServerSkeleton:
    """MCP Server Skeleton providing tool execution interfaces."""

    def __init__(self):
        self.tools = {
            "calendar_freebusy": fetch_attendee_freebusy,
            "room_search": room_search,
            "room_book": room_book,
            "zoom_create_meeting": zoom_create_meeting,
            "zoom_get_meeting": zoom_get_meeting,
        }
        self.tool_allowlists = {
            "scheduling_agent": frozenset({"calendar_freebusy", "zoom_create_meeting", "zoom_get_meeting"}),
            "room_booking_agent": frozenset({"room_search", "room_book", "zoom_create_meeting", "zoom_get_meeting"}),
            "agenda_agent": frozenset(),
            "minutes_agent": frozenset(),
            "action_tracker_agent": frozenset(),
            "reminder_agent": frozenset(),
            "distribution_agent": frozenset({"zoom_get_meeting"}),
            "orchestrator": frozenset({"calendar_freebusy", "room_search", "room_book", "zoom_create_meeting", "zoom_get_meeting"}),
        }
        self.tool_descriptions = {
            "calendar_freebusy": "Fetch attendee busy intervals",
            "room_search": "Search available rooms matching capacity, window, and equipment",
            "room_book": "Book a room for a meeting with double-booking prevention",
            "zoom_create_meeting": "Create a Zoom meeting with topic, start time, duration, and timezone",
            "zoom_get_meeting": "Retrieve Zoom meeting details by meeting ID",
        }

    def list_tools(self) -> list[dict[str, str]]:
        return [
            {"name": name, "description": description}
            for name, description in self.tool_descriptions.items()
        ]

    def call_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        agent_name: str | None = None,
    ) -> Any:
        if tool_name not in self.tools:
            raise ToolError(
                f"Tool '{tool_name}' is not registered.",
                tool_name=tool_name,
            )
        if agent_name is not None and tool_name not in self.tool_allowlists.get(agent_name, frozenset()):
            raise ToolError(
                f"Agent '{agent_name}' is not allowed to call '{tool_name}'.",
                tool_name=tool_name,
            )
        logger.info("Executing MCP Tool: %s", tool_name)
        return self.tools[tool_name](**arguments)


mcp_server = MCPServerSkeleton()

def serve(host: str = "0.0.0.0", port: int = 8765) -> None:
    """Expose the tool registry over a minimal JSON HTTP endpoint.

    The registry is the authoritative allowlist used by :meth:`MCPServerSkeleton.call_tool`,
    so this endpoint never bypasses the per-agent tool allowlists.
    """
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class _Handler(BaseHTTPRequestHandler):
        server_version = "MCPServerSkeleton/1.0"

        def _respond(self, payload: dict[str, Any], status: int = 200) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - stdlib naming
            if self.path.rstrip("/") in ("", "/tools"):
                self._respond({"tools": mcp_server.list_tools()})
            else:
                self._respond({"error": f"Unknown path {self.path}"}, 404)

        def do_POST(self) -> None:  # noqa: N802 - stdlib naming
            if self.path.rstrip("/") != "/call":
                self._respond({"error": f"Unknown path {self.path}"}, 404)
                return
            length = int(self.headers.get("Content-Length") or 0)
            try:
                arguments = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                self._respond({"error": "Request body must be valid JSON."}, 400)
                return
            if not isinstance(arguments, dict):
                self._respond({"error": "Request body must be a JSON object."}, 400)
                return
            tool_name = arguments.pop("tool_name", None)
            agent_name = arguments.pop("agent_name", None)
            try:
                result = mcp_server.call_tool(tool_name, arguments, agent_name)
            except ToolError as exc:
                self._respond({"error": exc.message, "code": exc.code}, 400)
                return
            self._respond({"result": result})

        def log_message(self, fmt: str, *args: Any) -> None:
            logger.info("mcp-http %s", fmt % args)

    httpd = ThreadingHTTPServer((host, port), _Handler)
    logger.info("Starting MCP Server Skeleton on %s:%d", host, port)
    logger.info("Available MCP tools: %s", json.dumps(mcp_server.list_tools()))
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down MCP server.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    import os

    serve(
        host=os.environ.get("MCP_HOST", "0.0.0.0"),
        port=int(os.environ.get("MCP_PORT", "8765")),
    )
