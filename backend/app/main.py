from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import OperationalError

from app.api.routes.actions import router as actions_router
from app.api.routes.agendas import router as agendas_router
from app.api.routes.auth import router as auth_router
from app.api.routes.jobs import router as jobs_router
from app.api.routes.meetings import router as meetings_router
from app.api.routes.memory import router as memory_router
from app.api.routes.minutes import router as minutes_router
from app.api.routes.rooms import router as rooms_router
from app.api.routes.schedule import router as schedule_router
from app.api.routes.traces import router as traces_router
from app.api.routes.users import router as users_router
from app.config import settings
from app.core.errors import AppError, app_exception_handler
from app.core.logging import setup_logging
from app.middleware.timing import TimingMiddleware
from app.services.job_worker import start_worker, stop_worker

logger = setup_logging()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Manage the background job worker for the lifetime of the API process."""
    startup_started = perf_counter()
    worker_started = perf_counter()
    start_worker()
    logger.info(
        "STARTUP worker_start_ms=%.2f total_ms=%.2f",
        (perf_counter() - worker_started) * 1000,
        (perf_counter() - startup_started) * 1000,
    )
    try:
        yield
    finally:
        stop_worker()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# Request timing — must be added before CORS so it wraps all requests
app.add_middleware(TimingMiddleware)

# CORS middleware for frontend UI
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handlers
app.add_exception_handler(AppError, app_exception_handler)


@app.exception_handler(OperationalError)
async def database_unavailable_handler(
    request: Request,
    exc: OperationalError,
) -> JSONResponse:
    logger.error(
        "Database unavailable for %s %s (%s)",
        request.method,
        request.url.path,
        type(exc).__name__,
    )
    return JSONResponse(
        status_code=503,
        content={"detail": "Database temporarily unavailable. Please try again."},
        headers={"Retry-After": "2"},
    )


# Include Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(meetings_router, prefix=settings.API_V1_STR)
app.include_router(rooms_router, prefix=settings.API_V1_STR)
app.include_router(agendas_router, prefix=settings.API_V1_STR)
app.include_router(minutes_router, prefix=settings.API_V1_STR)
app.include_router(actions_router, prefix=settings.API_V1_STR)
app.include_router(memory_router, prefix=settings.API_V1_STR)
app.include_router(schedule_router, prefix=settings.API_V1_STR)
app.include_router(traces_router, prefix=settings.API_V1_STR)
app.include_router(users_router, prefix=settings.API_V1_STR)
app.include_router(jobs_router, prefix=settings.API_V1_STR)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "Meeting Organizer Agent API is running."}


@app.get("/health")
def health_check() -> dict[str, str]:
    from sqlalchemy import text

    from app.db.session import SessionLocal
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        db_status = "ok"
    except OperationalError as exc:
        logger.warning("Health check database probe failed (%s)", type(exc).__name__)
        db_status = "unhealthy"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "version": settings.VERSION,
        "llm_model": settings.LLM_MODEL,
    }


@app.get("/ready")
def readiness_check() -> dict[str, str]:
    # Keep readiness checks independent of the database; /health reports DB status.
    return {"status": "ready"}
