from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.actions import router as actions_router
from app.api.routes.agendas import router as agendas_router
from app.api.routes.auth import router as auth_router
from app.api.routes.meetings import router as meetings_router
from app.api.routes.jobs import router as jobs_router
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

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
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


@app.on_event("startup")
def _create_new_tables() -> None:
    """Ensure any tables added since initial migration exist (e.g. llm_cache)."""
    from app.db.base import Base  # noqa: PLC0415
    from app.db.session import engine  # noqa: PLC0415
    import app.db.models  # noqa: F401, PLC0415 — registers all ORM classes
    Base.metadata.create_all(bind=engine)
    start_worker()


@app.on_event("shutdown")
def _stop_job_worker() -> None:
    stop_worker()

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
    db_status = "ok"
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
    except Exception as exc:
        db_status = f"unhealthy: {exc}"

    return {
        "status": "ok" if db_status == "ok" else "degraded",
        "database": db_status,
        "version": settings.VERSION,
        "llm_model": settings.LLM_MODEL,
    }


@app.get("/ready")
def readiness_check() -> dict[str, str]:
    return {"status": "ready"}
