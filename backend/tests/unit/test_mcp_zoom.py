import pytest
from app.core.errors import ToolError, ValidationFailed
from mcp_server.server import mcp_server
from mcp_server.tools.zoom_tools import ZoomClient, zoom_client


def test_mcp_zoom_create_and_get_meeting_mock():
    # Test creation via MCP server call_tool
    args = {
        "topic": "Faculty Strategic Review",
        "start_time": "2026-11-05T10:00:00Z",
        "duration_minutes": 45,
        "timezone": "Asia/Kolkata",
        "idempotency_key": "review_meeting_20261105",
    }
    result = mcp_server.call_tool(
        tool_name="zoom_create_meeting",
        arguments=args,
        agent_name="scheduling_agent",
    )
    assert result["topic"] == "Faculty Strategic Review"
    assert "id" in result
    assert result["duration"] == 45
    assert "join_url" in result
    assert result["is_mock"] is True
    # Host URL should be omitted by default for security
    assert "start_url" not in result

    # Retrieve meeting details via zoom_get_meeting
    meeting_id = result["id"]
    get_res = mcp_server.call_tool(
        tool_name="zoom_get_meeting",
        arguments={"meeting_id": meeting_id},
        agent_name="distribution_agent",
    )
    assert get_res["id"] == meeting_id
    assert get_res["topic"] == "Faculty Strategic Review"


def test_mcp_zoom_idempotency_prevents_duplicate_meetings():
    key = "unique_sprint_sync_key"
    args = {
        "topic": "Sprint Sync",
        "start_time": "2026-11-06T14:00:00Z",
        "duration_minutes": 30,
        "idempotency_key": key,
    }
    res1 = mcp_server.call_tool("zoom_create_meeting", args, agent_name="scheduling_agent")
    res2 = mcp_server.call_tool("zoom_create_meeting", args, agent_name="scheduling_agent")
    assert res1["id"] == res2["id"]
    assert res1["join_url"] == res2["join_url"]


def test_mcp_zoom_host_url_restricted():
    args = {
        "topic": "Admin Meeting",
        "start_time": "2026-11-07T11:00:00Z",
        "duration_minutes": 60,
        "include_host_url": True,
    }
    res = mcp_server.call_tool("zoom_create_meeting", args, agent_name="orchestrator")
    assert "start_url" in res
    assert "mock_host_token" in res["start_url"]


def test_mcp_zoom_invalid_arguments_validation():
    # Empty topic
    with pytest.raises(ValidationFailed):
        mcp_server.call_tool(
            "zoom_create_meeting",
            {"topic": "", "start_time": "2026-11-05T10:00:00Z"},
            agent_name="scheduling_agent",
        )

    # Invalid duration
    with pytest.raises(ValidationFailed):
        mcp_server.call_tool(
            "zoom_create_meeting",
            {"topic": "Valid Topic", "start_time": "2026-11-05T10:00:00Z", "duration_minutes": -10},
            agent_name="scheduling_agent",
        )


def test_mcp_zoom_unauthorized_agent_permission_rejection():
    # minutes_agent is not allowed to create zoom meetings
    with pytest.raises(ToolError, match="not allowed"):
        mcp_server.call_tool(
            "zoom_create_meeting",
            {"topic": "Unauthorized", "start_time": "2026-11-05T10:00:00Z"},
            agent_name="minutes_agent",
        )
