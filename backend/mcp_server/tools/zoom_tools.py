import hashlib
import time
from typing import Any

import httpx
from app.config import settings
from app.core.errors import ToolError, ValidationFailed
from app.core.logging import setup_logging
from dateutil.parser import parse as parse_date

logger = setup_logging()

# In-memory mock storage for created Zoom meetings (for tests / when real Zoom API keys are absent)
_MOCK_ZOOM_MEETINGS: dict[str, dict[str, Any]] = {}
_IDEMPOTENCY_STORE: dict[str, str] = {}  # idempotency_key -> meeting_id
_ZOOM_MEETING_CREATE_SCOPES = frozenset(
    {"meeting:write:meeting", "meeting:write:meeting:admin"}
)


class ZoomClient:
    """Zoom API client supporting OAuth Server-to-Server / Mock integration with retry safety."""

    def __init__(
        self,
        account_id: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        allow_mock: bool = False,
    ):
        self.account_id = account_id if account_id is not None else settings.ZOOM_ACCOUNT_ID
        self.client_id = client_id if client_id is not None else settings.ZOOM_CLIENT_ID
        self.client_secret = client_secret if client_secret is not None else settings.ZOOM_CLIENT_SECRET
        self.allow_mock = allow_mock
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0
        self._granted_scopes: frozenset[str] | None = None

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
                response_scopes = data.get("scope")
                if isinstance(response_scopes, str):
                    self._granted_scopes = frozenset(response_scopes.replace(",", " ").split())
                elif isinstance(response_scopes, list) and all(isinstance(scope, str) for scope in response_scopes):
                    self._granted_scopes = frozenset(response_scopes)
                else:
                    self._granted_scopes = None
                return self._access_token
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500:
                    try:
                        error_data = exc.response.json()
                    except ValueError:
                        error_data = {}

                    zoom_code = error_data.get("error") or error_data.get("code")
                    zoom_message = (
                        error_data.get("reason")
                        or error_data.get("error_description")
                        or error_data.get("message")
                    )
                    if isinstance(zoom_message, str):
                        for credential in (self.account_id, self.client_id, self.client_secret):
                            if credential:
                                zoom_message = zoom_message.replace(credential, "[redacted]")

                    message = f"Zoom authentication failed with HTTP {exc.response.status_code}"
                    if isinstance(zoom_code, (int, str)):
                        message += f" ({str(zoom_code)[:100]})"
                    if isinstance(zoom_message, str) and zoom_message:
                        message += f": {zoom_message[:500]}"

                    raise ToolError(
                        message,
                        tool_name="zoom.get_access_token",
                        details={
                            "http_status": exc.response.status_code,
                            "zoom_code": zoom_code if isinstance(zoom_code, (int, str)) else None,
                        },
                    ) from exc
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

        # Mocks must be explicitly enabled by tests; never return fake Zoom URLs.
        if not self.has_live_credentials:
            if not self.allow_mock:
                raise ToolError(
                    "Zoom is not configured. Set ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, and "
                    "ZOOM_CLIENT_SECRET in the local .env file.",
                    tool_name="zoom.create_meeting",
                )
            mock_digest = hashlib.md5(
                f"{topic}_{start_time_iso}_{idempotency_key}".encode()
            ).hexdigest()[:10]
            meeting_id = f"mock-{int(mock_digest, 16)}"
            meeting_record = {
                "id": meeting_id,
                "topic": topic,
                "start_time": start_dt.isoformat(),
                "duration": duration_minutes,
                "timezone": timezone_str,
                "status": "waiting",
                "is_mock": True,
            }
            _MOCK_ZOOM_MEETINGS[meeting_id] = meeting_record
            if idempotency_key:
                _IDEMPOTENCY_STORE[idempotency_key] = meeting_id

            return dict(meeting_record)

        # Live Zoom API call
        token = self._get_access_token()
        if (
            self._granted_scopes is not None
            and not _ZOOM_MEETING_CREATE_SCOPES.intersection(self._granted_scopes)
        ):
            required_scopes = sorted(_ZOOM_MEETING_CREATE_SCOPES)
            raise ToolError(
                "The Zoom access token lacks a meeting-creation scope. Add "
                f"{' or '.join(required_scopes)} to the existing Zoom Server-to-Server OAuth app, "
                "then restart the backend to fetch a token with the updated scope. "
                "The existing account ID, client ID, and client secret do not need to change.",
                tool_name="zoom.create_meeting",
                details={"required_scopes": required_scopes},
            )
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
                if exc.response.status_code < 500:
                    try:
                        error_data = exc.response.json()
                    except ValueError:
                        error_data = {}

                    zoom_code = error_data.get("code")
                    zoom_message = error_data.get("message")
                    message = f"Zoom API meeting creation failed with status {exc.response.status_code}"
                    if zoom_code is not None:
                        message += f" (Zoom code {zoom_code})"
                    if isinstance(zoom_message, str) and zoom_message:
                        message += f": {zoom_message[:500]}"

                    raise ToolError(
                        message,
                        tool_name="zoom.create_meeting",
                        details={"http_status": exc.response.status_code, "zoom_code": zoom_code},
                    ) from exc
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
