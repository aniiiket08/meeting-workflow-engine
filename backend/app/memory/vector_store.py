import json
import math
import re
from pathlib import Path
from typing import Any
from sqlalchemy.orm import Session

from app.config import settings
from app.core.errors import ToolError
from app.core.logging import setup_logging
from app.db.models.agenda import Decision
from app.db.models.meeting import Meeting
from app.db.models.minutes import Minutes, MinutesStatus

logger = setup_logging()

SEED_DATA_PATH = Path(__file__).resolve().parent.parent.parent.parent / "data" / "seed" / "past_meetings.json"

STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for", "with", "about",
    "is", "was", "were", "what", "did", "we", "our", "us", "of", "by", "that", "this",
    "how", "when", "where", "who", "which", "are", "be", "been", "have", "has", "had",
}


def _tokenize(text: str) -> list[str]:
    words = re.findall(r"\b[a-zA-Z0-9_\$]+\b", text.lower())
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


class MemoryStore:
    """Vector / Document store for meeting minutes and decisions RAG retrieval."""

    def __init__(self, data_path: Path = SEED_DATA_PATH):
        self.data_path = data_path
        self.documents: list[dict[str, Any]] = []
        self.load_error: str | None = None
        self._load_seed_data()

    def _load_seed_data(self) -> None:
        if not self.data_path.exists():
            self.load_error = f"Past-meeting memory file is missing: {self.data_path}"
            logger.error(self.load_error)
            return
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                documents = json.load(f)
            if not isinstance(documents, list):
                raise ValueError("Past-meeting memory must be a JSON list.")
            self.documents = list(documents)
            logger.info("Loaded %d past meeting records into MemoryStore.", len(self.documents))
        except Exception as exc:
            self.load_error = "Past-meeting memory could not be loaded."
            logger.exception("Could not load past-meeting memory")

    def add_document(self, meeting_id: int, title: str, text: str, date_str: str) -> None:
        """Add or update an indexed meeting document, preventing stale duplicates."""
        existing_idx = next(
            (idx for idx, doc in enumerate(self.documents) if doc.get("meeting_id") == meeting_id),
            None,
        )
        doc = {
            "meeting_id": meeting_id,
            "title": title,
            "text": text,
            "date": date_str,
        }
        if existing_idx is not None:
            self.documents[existing_idx] = doc
        else:
            self.documents.append(doc)
        logger.info("Indexed meeting %d ('%s') into memory store.", meeting_id, title)

    def sync_from_database(self, db: Session) -> int:
        """Sync approved meetings and minutes from the SQL database into MemoryStore."""
        approved_minutes = (
            db.query(Minutes)
            .filter(Minutes.status == MinutesStatus.APPROVED)
            .order_by(Minutes.version.desc())
            .all()
        )
        synced = 0
        seen_meetings: set[int] = set()

        for min_record in approved_minutes:
            if min_record.meeting_id in seen_meetings:
                continue
            seen_meetings.add(min_record.meeting_id)

            meeting = db.query(Meeting).filter(Meeting.id == min_record.meeting_id).first()
            if not meeting:
                continue

            decisions = db.query(Decision).filter(Decision.meeting_id == min_record.meeting_id).all()
            decision_texts = " ".join(f"Decision: {d.text}" for d in decisions)
            date_str = meeting.start_time.strftime("%Y-%m-%d") if meeting.start_time else (
                meeting.target_date.strftime("%Y-%m-%d") if meeting.target_date else "Recent"
            )

            text_parts = [min_record.summary or ""]
            if min_record.key_discussion_points:
                text_parts.append(" ".join(min_record.key_discussion_points))
            if decision_texts:
                text_parts.append(decision_texts)

            full_text = " ".join(text_parts).strip()
            self.add_document(
                meeting_id=meeting.id,
                title=meeting.title,
                text=full_text,
                date_str=date_str,
            )
            synced += 1

        return synced

    def search(self, query: str, top_k: int = 3, db: Session | None = None) -> list[dict[str, Any]]:
        """Semantic BM25-style keyword and recency retrieval over meeting minutes."""
        if self.load_error:
            raise ToolError(self.load_error, tool_name="memory_store.search")

        if db is not None:
            self.sync_from_database(db)

        if not query.strip() or top_k <= 0:
            return []

        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        doc_count = len(self.documents)
        if doc_count == 0:
            return []

        # Token frequencies
        df: dict[str, int] = {}
        for doc in self.documents:
            doc_tokens = set(_tokenize(f"{doc['title']} {doc['text']}"))
            for qt in query_tokens:
                if qt in doc_tokens:
                    df[qt] = df.get(qt, 0) + 1

        scored_docs: list[tuple[float, dict[str, Any]]] = []

        for doc in self.documents:
            title_text = doc.get("title", "")
            body_text = doc.get("text", "")
            title_tokens = _tokenize(title_text)
            body_tokens = _tokenize(body_text)

            score = 0.0
            matched_terms = 0

            for qt in query_tokens:
                # IDF
                doc_freq = df.get(qt, 0)
                if doc_freq == 0:
                    continue
                idf = math.log(1.0 + (doc_count - doc_freq + 0.5) / (doc_freq + 0.5))

                # Term counts
                title_matches = title_tokens.count(qt)
                body_matches = body_tokens.count(qt)

                if title_matches or body_matches:
                    matched_terms += 1
                    # Heavy weight on title relevance and exact keywords
                    term_score = (title_matches * 3.0 + body_matches * 1.0) * idf
                    score += term_score

            # Require relevant overlap (do not return matches solely because they exist)
            if matched_terms > 0:
                scored_docs.append((score, doc))

        # Sort descending by relevance score, then by date descending
        scored_docs.sort(key=lambda x: (x[0], x[1].get("date", "")), reverse=True)
        return [doc for score, doc in scored_docs[:top_k]]


memory_store = MemoryStore()
