import httpx
import pytest
from app.core.errors import ToolError, ValidationFailed
from mcp_server.server import mcp_server
from mcp_server.tools.zoom_tools import ZoomClient, zoom_client


@pytest.fixture(autouse=True)
def use_mock_zoom(monkeypatch):
    monkeypatch.setattr(zoom_client, "account_id", None)
    monkeypatch.setattr(zoom_client, "client_id", None)
    monkeypatch.setattr(zoom_client, "client_secret", None)
    monkeypatch.setattr(zoom_client, "allow_mock", True)


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
    assert result["id"].startswith("mock-")
    assert "join_url" not in result
    assert result["is_mock"] is True
    # Mock meetings must never expose URLs that appear to be live Zoom links.
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
    assert "join_url" not in res1
    assert "join_url" not in res2


def test_mcp_zoom_host_url_restricted():
    args = {
        "topic": "Admin Meeting",
        "start_time": "2026-11-07T11:00:00Z",
        "duration_minutes": 60,
        "include_host_url": True,
    }
    res = mcp_server.call_tool("zoom_create_meeting", args, agent_name="orchestrator")
    assert "start_url" not in res
    assert "join_url" not in res


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


def test_zoom_client_requires_credentials_outside_explicit_mock_mode():
    client = ZoomClient(account_id="", client_id="", client_secret="")

    with pytest.raises(ToolError, match="Zoom is not configured"):
        client.create_meeting(
            topic="Test meeting",
            start_time_iso="2026-11-05T10:00:00Z",
            idempotency_key="missing-zoom-config",
        )


def test_zoom_client_reports_oauth_rejection_without_retrying_or_exposing_credentials(monkeypatch):
    client = ZoomClient(
        account_id="test-account",
        client_id="test-client",
        client_secret="sensitive-test-secret",
    )
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        request = httpx.Request("POST", url)
        return httpx.Response(
            400,
            request=request,
            json={
                "error": "invalid_client",
                "reason": "The provided client secret is invalid.",
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(ToolError, match="invalid_client.*client secret is invalid") as exc_info:
        client.create_meeting(
            topic="Test meeting",
            start_time_iso="2026-11-05T10:00:00Z",
        )

    assert calls == ["https://zoom.us/oauth/token"]
    assert "sensitive-test-secret" not in str(exc_info.value)
    assert exc_info.value.details == {
        "tool": "zoom.get_access_token",
        "http_status": 400,
        "zoom_code": "invalid_client",
    }


def test_zoom_client_uses_oauth_and_returns_real_join_url(monkeypatch):
    client = ZoomClient(
        account_id="test-account",
        client_id="test-client",
        client_secret="test-secret",
    )
    calls = []
    meeting_payloads = []

    def fake_post(url, **kwargs):
        calls.append(url)
        if url == "https://api.zoom.us/v2/users/me/meetings":
            meeting_payloads.append(kwargs["json"])
        request = httpx.Request("POST", url)
        if url == "https://zoom.us/oauth/token":
            return httpx.Response(
                200,
                request=request,
                json={"access_token": "test-token", "expires_in": 3600},
            )
        assert kwargs["headers"]["Authorization"] == "Bearer test-token"
        return httpx.Response(
            201,
            request=request,
            json={
                "id": 123456789,
                "topic": "Authorized test",
                "start_time": "2026-11-05T10:00:00Z",
                "duration": 30,
                "timezone": "UTC",
                "join_url": "https://zoom.us/j/123456789",
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    meeting = client.create_meeting(
        topic="Authorized test",
        start_time_iso="2026-11-05T10:00:00Z",
        duration_minutes=30,
    )

    assert len(calls) == 2
    assert meeting["id"] == "123456789"
    assert meeting["join_url"] == "https://zoom.us/j/123456789"
    assert meeting["is_mock"] is False
    assert meeting_payloads == [
        {
            "topic": "Authorized test",
            "type": 2,
            "start_time": "2026-11-05T10:00:00Z",
            "duration": 30,
            "timezone": "UTC",
        }
    ]


def test_zoom_client_rejects_token_missing_meeting_scope(monkeypatch):
    client = ZoomClient(
        account_id="test-account",
        client_id="test-client",
        client_secret="test-secret",
    )
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        request = httpx.Request("POST", url)
        return httpx.Response(
            200,
            request=request,
            json={
                "access_token": "test-token",
                "expires_in": 3600,
                "scope": "team_chat:update:invitation:admin",
            },
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(ToolError, match="lacks a meeting-creation scope") as exc_info:
        client.create_meeting(
            topic="Test meeting",
            start_time_iso="2026-11-05T10:00:00Z",
        )

    assert calls == ["https://zoom.us/oauth/token"]
    assert exc_info.value.details["required_scopes"] == [
        "meeting:write:meeting",
        "meeting:write:meeting:admin",
    ]


def test_zoom_client_reports_zoom_rejection_without_retrying(monkeypatch):
    client = ZoomClient(
        account_id="test-account",
        client_id="test-client",
        client_secret="test-secret",
    )
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        request = httpx.Request("POST", url)
        if url == "https://zoom.us/oauth/token":
            return httpx.Response(
                200,
                request=request,
                json={"access_token": "test-token", "expires_in": 3600},
            )
        return httpx.Response(
            400,
            request=request,
            json={"code": 300, "message": "Invalid meeting start time."},
        )

    monkeypatch.setattr(httpx, "post", fake_post)
    with pytest.raises(ToolError, match="Zoom code 300.*Invalid meeting start time") as exc_info:
        client.create_meeting(
            topic="Rejected meeting",
            start_time_iso="2026-11-05T10:00:00Z",
            duration_minutes=30,
        )

    assert calls == ["https://zoom.us/oauth/token", "https://api.zoom.us/v2/users/me/meetings"]
    assert exc_info.value.details == {"tool": "zoom.create_meeting", "http_status": 400, "zoom_code": 300}
