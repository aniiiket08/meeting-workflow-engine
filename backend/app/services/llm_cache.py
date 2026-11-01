"""
DB-backed LLM response cache — no Redis, no external services.

Cache key = SHA-256(model, system prompt, prompt version, prompt).
TTL = 24 hours. Stale entries are filtered on read; a separate purge helper can
be called from a scheduled task or on startup.
"""
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.logging import setup_logging
from app.db.models.llm_cache import LLMCache

logger = setup_logging()

_TTL_HOURS = 24
PROMPT_VERSION = "1"


def make_cache_key(
    model: str,
    system_prompt: str,
    prompt: str,
    prompt_version: str = PROMPT_VERSION,
) -> str:
    """Return a 64-character hex SHA-256 digest used as the cache lookup key."""
    raw = "\0".join((model, system_prompt, prompt_version, prompt))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached(db: Session, prompt_hash: str) -> Optional[str]:
    """Return cached response text, or None if not found or expired."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_TTL_HOURS)
    row = (
        db.query(LLMCache)
        .filter(LLMCache.prompt_hash == prompt_hash, LLMCache.created_at >= cutoff)
        .first()
    )
    if row:
        logger.debug("LLM cache HIT for hash=%s", prompt_hash[:12])
        return row.response_text
    return None


def set_cache(
    db: Session,
    prompt_hash: str,
    response_text: str,
    prompt_tokens: Optional[int] = None,
    completion_tokens: Optional[int] = None,
) -> None:
    """Insert or update a cache entry. Silently swallows DB errors."""
    try:
        existing = (
            db.query(LLMCache)
            .filter(LLMCache.prompt_hash == prompt_hash)
            .first()
        )
        if existing:
            existing.response_text = response_text
            existing.created_at = datetime.now(timezone.utc)
            existing.prompt_tokens = prompt_tokens
            existing.completion_tokens = completion_tokens
        else:
            db.add(
                LLMCache(
                    prompt_hash=prompt_hash,
                    response_text=response_text,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                )
            )
        db.commit()
        logger.debug("LLM cache SET for hash=%s", prompt_hash[:12])
    except Exception as exc:  # noqa: BLE001
        logger.warning("LLM cache write failed (non-fatal): %s", exc)
        db.rollback()


def purge_stale(db: Session) -> int:
    """Delete cache entries older than TTL. Returns count deleted."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_TTL_HOURS)
    deleted = db.query(LLMCache).filter(LLMCache.created_at < cutoff).delete()
    db.commit()
    return deleted
