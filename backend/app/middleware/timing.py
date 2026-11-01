"""
Request timing middleware — logs method, path and elapsed_ms for every request.
Results feed p50/p90 analysis in bench_api.py and Render dashboard log queries.
"""
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.logging import setup_logging

logger = setup_logging()

SKIP_PATHS = {"/", "/health", "/ready"}


class TimingMiddleware(BaseHTTPMiddleware):
    """Adds an X-Response-Time header and emits a structured log line per request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start) * 1000

        path = request.url.path
        method = request.method

        # Always attach the header so the frontend can read it
        response.headers["X-Response-Time"] = f"{elapsed_ms:.2f}ms"

        if path not in SKIP_PATHS:
            logger.info(
                "REQUEST %s %s %.2fms status=%d",
                method,
                path,
                elapsed_ms,
                response.status_code,
            )

        return response

