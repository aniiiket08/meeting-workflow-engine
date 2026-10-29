import hashlib
import os
import time
from datetime import datetime, timezone
from typing import Any
import httpx
from dateutil.parser import parse as parse_date

from app.core.errors import ToolError, ValidationFailed
from app.core.logging import setup_logging

logger = setup_logging()

# In-memory mock storage for created Zoom meetings (for tests / when real Zoom API keys are absent)
_MOCK_ZOOM_MEETINGS: dict[str, dict[str, Any]] = {}
_IDEMPOTENCY_STORE: dict[str, str] = {}  # idempotency_key -> meeting_id


class ZoomClient:
    """Zoom API client supporting OAuth Server-to-Server / Mock integration with retry safety."""

    def __init__(
        self,
        account_id: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ):
        self.account_id = account_id or os.getenv("ZOOM_ACCOUNT_ID")
        self.client_id = client_id or os.getenv("ZOOM_CLIENT_ID")
        self.client_secret = client_secret or os.getenv("ZOOM_CLIENT_SECRET")
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

    @property
    def has_live_credentials(self) -> bool:
        return bool(self.account_id and self.client_id and self.client_secret)

    def _get_access_token(self) -> str:
        """Fetch or refresh Zoom OAuth Server-to-Server token."""
        if self._access_token and time.time() < (self._token_expires_at - 60):
            return self._access_token

        if not self.has_live_credentials:
            raise ToolError(
                "Live Zoom credentials are not configured.",
                tool_name="zoom.get_access_token",
            )

        token_url = "https://zoom.us/oauth/token"
        params = {
            "grant_type": "account_credentials",
            "account_id": self.account_id,
        }
        for attempt in range(3):
            try:
                response = httpx.post(
                    token_url,
                    params=params,
                    auth=(self.client_id or "", self.client_secret or ""),
                    timeout=30.0,
                )
                if response.status_code == 429:
                    retry_after = float(response.headers.get("retry-after", "2"))
                    time.sleep(retry_after)
                    continue
                response.raise_for_status()
                data = response.json()
                self._access_token = data["access_token"]
                self._token_expires_at = time.time() + data.get("expires_in", 3600)
                return self._access_token
            except httpx.HTTPStatusError as exc:
                if attempt == 2:
                    raise ToolError(
                        f"Zoom authentication failed with HTTP {exc.response.status_code}.",
                        tool_name="zoom.get_access_token",
                    ) from exc
                time.sleep(2**attempt)
            except Exception as exc:
                if attempt == 2:
                    raise ToolError("Zoom authentication request failed.", tool_name="zoom.get_access_token") from exc
                time.sleep(2**attempt)

        raise ToolError("Could not authenticate with Zoom.", tool_name="zoom.get_access_token")

    def create_meeting(
        self,
        topic: str,
        start_time_iso: str,
        duration_minutes: int = 60,
        timezone_str: str = "UTC",
        idempotency_key: str | None = None,
        include_host_url: bool = False,
    ) -> dict[str, Any]:
        """Create a Zoom meeting, preventing duplicates via idempotency_key."""
        if not topic.strip():
            raise ValidationFailed("Meeting topic cannot be empty.")
        if duration_minutes <= 0:
            raise ValidationFailed("Meeting duration must be greater than zero.")

        try:
            start_dt = parse_date(start_time_iso)
        except Exception as exc:
            raise ValidationFailed(f"Invalid start_time format: {exc}")

        # Idempotency check: if already created under this key, return the existing record
        if idempotency_key and idempotency_key in _IDEMPOTENCY_STORE:
            existing_id = _IDEMPOTENCY_STORE[idempotency_key]
            existing = _MOCK_ZOOM_MEETINGS.get(existing_id)
            if existing:
                res = dict(existing)
                if not include_host_url:
                    res.pop("start_url", None)
                return res

        # Fallback to deterministic clean mock if live credentials not configured
        if not self.has_live_credentials:
            meeting_id = str(int(hashlib.md5(f"{topic}_{start_time_iso}_{idempotency_key}".encode()).hexdigest()[:10], 16))
            meeting_record = {
                "id": meeting_id,
                "topic": topic,
                "start_time": start_dt.isoformat(),
                "duration": duration_minutes,
                "timezone": timezone_str,
                "join_url": f"https://zoom.us/j/{meeting_id}",
                "start_url": f"https://zoom.us/s/{meeting_id}?zak=mock_host_token",
                "status": "waiting",
                "is_mock": True,
            }
            _MOCK_ZOOM_MEETINGS[meeting_id] = meeting_record
            if idempotency_key:
                _IDEMPOTENCY_STORE[idempotency_key] = meeting_id

            out = dict(meeting_record)
            if not include_host_url:
                out.pop("start_url", None)
            return out

        # Live Zoom API call
        token = self._get_access_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        payload = {
            "topic": topic,
            "type": 2,  # Scheduled meeting
            "start_time": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "duration": duration_minutes,
            "timezone": timezone_str,
        }

        url = "https://api.zoom.us/v2/users/me/meetings"
        for attempt in range(3):
            try:
                response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
                if response.status_code == 429:
                    retry_after = float(response.headers.get("retry-after", "2"))
                    time.sleep(retry_after)
                    continue
                response.raise_for_status()
                data = response.json()
                meeting_id = str(data["id"])
                meeting_record = {
                    "id": meeting_id,
                    "topic": data.get("topic", topic),
                    "start_time": data.get("start_time"),
                    "duration": data.get("duration", duration_minutes),
                    "timezone": data.get("timezone", timezone_str),
                    "join_url": data.get("join_url"),
                    "start_url": data.get("start_url"),
                    "status": data.get("status", "waiting"),
                    "is_mock": False,
                }
                _MOCK_ZOOM_MEETINGS[meeting_id] = meeting_record
                if idempotency_key:
                    _IDEMPOTENCY_STORE[idempotency_key] = meeting_id

                out = dict(meeting_record)
                if not include_host_url:
                    out.pop("start_url", None)
                return out
            except httpx.HTTPStatusError as exc:
                if attempt == 2:
                    raise ToolError(
                        f"Zoom API meeting creation failed with status {exc.response.status_code}.",
                        tool_name="zoom.create_meeting",
                    ) from exc
                time.sleep(2**attempt)
            except Exception as exc:
                if attempt == 2:
                    raise ToolError("Zoom API meeting creation request failed.", tool_name="zoom.create_meeting") from exc
                time.sleep(2**attempt)

        raise ToolError("Failed to create Zoom meeting after retries.", tool_name="zoom.create_meeting")

    def get_meeting(
        self,
        meeting_id: str,
        include_host_url: bool = False,
    ) -> dict[str, Any]:
        """Retrieve Zoom meeting details."""
        if not meeting_id:
            raise ValidationFailed("meeting_id is required.")

        # Check mock / cached store first
        if meeting_id in _MOCK_ZOOM_MEETINGS:
            data = dict(_MOCK_ZOOM_MEETINGS[meeting_id])
            if not include_host_url:
                data.pop("start_url", None)
            return data

        if not self.has_live_credentials:
            raise ToolError(f"Zoom meeting '{meeting_id}' not found.", tool_name="zoom.get_meeting")

        token = self._get_access_token()
        headers = {"Authorization": f"Bearer {token}"}
        url = f"https://api.zoom.us/v2/meetings/{meeting_id}"

        try:
            response = httpx.get(url, headers=headers, timeout=30.0)
            if response.status_code == 404:
                raise ToolError(f"Zoom meeting '{meeting_id}' not found.", tool_name="zoom.get_meeting")
            response.raise_for_status()
            data = response.json()
            record = {
                "id": str(data["id"]),
                "topic": data.get("topic"),
                "start_time": data.get("start_time"),
                "duration": data.get("duration"),
                "timezone": data.get("timezone"),
                "join_url": data.get("join_url"),
                "start_url": data.get("start_url"),
                "status": data.get("status"),
                "is_mock": False,
            }
            if not include_host_url:
                record.pop("start_url", None)
            return record
        except ToolError:
            raise
        except Exception as exc:
            raise ToolError(f"Failed to fetch Zoom meeting: {exc}", tool_name="zoom.get_meeting") from exc


zoom_client = ZoomClient()


def zoom_create_meeting(
    topic: str,
    start_time: str,
    duration_minutes: int = 60,
    timezone: str = "UTC",
    idempotency_key: str | None = None,
    include_host_url: bool = False,
) -> dict[str, Any]:
    """MCP Tool: Create a Zoom meeting."""
    return zoom_client.create_meeting(
        topic=topic,
        start_time_iso=start_time,
        duration_minutes=duration_minutes,
        timezone_str=timezone,
        idempotency_key=idempotency_key,
        include_host_url=include_host_url,
    )


def zoom_get_meeting(
    meeting_id: str,
    include_host_url: bool = False,
) -> dict[str, Any]:
    """MCP Tool: Retrieve Zoom meeting details."""
    return zoom_client.get_meeting(
        meeting_id=meeting_id,
        include_host_url=include_host_url,
    )
