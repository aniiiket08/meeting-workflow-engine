from typing import Any
from fastapi import Request, status
from fastapi.responses import JSONResponse
from app.core.logging import logger


class AppError(Exception):
    """Base application exception for structured error responses."""

    def __init__(
        self,
        message: str,
        code: str = "app_error",
        http_status: int = status.HTTP_400_BAD_REQUEST,
        action: str | None = None,
        details: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status
        self.action = action
        self.details = details or {}


class ToolError(AppError):
    """Raised when an external MCP tool or service fails."""

    def __init__(self, message: str, tool_name: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            code="tool_error",
            http_status=status.HTTP_502_BAD_GATEWAY,
            action="retry_operation",
            details={"tool": tool_name, **(details or {})},
        )


class LLMError(AppError):
    """Raised when an LLM call fails or outputs unrepairable invalid JSON/schema."""

    def __init__(self, message: str, model: str | None = None, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            code="llm_error",
            http_status=status.HTTP_502_BAD_GATEWAY,
            action="retry_llm_request",
            details={"model": model, **(details or {})},
        )


class ValidationFailed(AppError):
    """Raised when domain validation or schema check fails."""

    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            message=message,
            code="validation_failed",
            http_status=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
            action="fix_input_data",
            details=details,
        )


class ApprovalRequired(AppError):
    """Raised when an agent attempts an outbound action without human approval."""

    def __init__(self, message: str = "Human approval required before releasing artifacts."):
        super().__init__(
            message=message,
            code="approval_required",
            http_status=status.HTTP_403_FORBIDDEN,
            action="submit_for_approval",
        )


class Conflict(AppError):
    """Raised when a resource or room scheduling conflict occurs."""

    def __init__(self, message: str, action: str = "choose_another_option"):
        super().__init__(
            message=message,
            code="conflict",
            http_status=status.HTTP_409_CONFLICT,
            action=action,
        )


class NotFound(AppError):
    """Raised when a requested resource is not found."""

    def __init__(self, entity: str, identifier: str | int):
        super().__init__(
            message=f"{entity} with ID '{identifier}' was not found.",
            code="not_found",
            http_status=status.HTTP_404_NOT_FOUND,
            action="check_resource_id",
        )


async def app_exception_handler(request: Request, exc: AppError) -> JSONResponse:
    """Global FastAPI exception handler converting AppError into structured JSON responses."""
    logger.error("AppError [%s] path=%s: %s", exc.code, request.url.path, exc.message)
    payload = {
        "error": {
            "code": exc.code,
            "message": exc.message,
        }
    }
    if exc.action:
        payload["error"]["action"] = exc.action
    if exc.details:
        payload["error"]["details"] = exc.details

    return JSONResponse(status_code=exc.http_status, content=payload)
