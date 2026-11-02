import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


@pytest.mark.asyncio
async def test_stdio_server_supports_standard_mcp_tool_listing_and_calls():
    project_root = Path(__file__).resolve().parents[3]
    env = os.environ.copy()
    backend_path = str(project_root / "backend")
    env["PYTHONPATH"] = os.pathsep.join(
        path for path in (backend_path, env.get("PYTHONPATH", "")) if path
    )
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.stdio_server"],
        cwd=project_root,
        env=env,
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.list_tools()

            assert {tool.name for tool in result.tools} == {
                "calendar_freebusy",
                "room_search",
                "room_book",
                "zoom_create_meeting",
                "zoom_get_meeting",
            }

            call_result = await session.call_tool(
                "calendar_freebusy",
                {"emails": ["nobody@example.test"]},
            )
            assert not call_result.is_error
