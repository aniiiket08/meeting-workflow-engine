"""SQLAlchemy model for DB-backed LLM response cache (no Redis required)."""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.base import Base


class LLMCache(Base):
    """Stores prompt→response mappings to avoid redundant Gemini API calls."""

    __tablename__ = "llm_cache"

    id = Column(Integer, primary_key=True, index=True)
    prompt_hash = Column(String(64), unique=True, index=True, nullable=False)
    response_text = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)

