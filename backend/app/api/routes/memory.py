from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
from app.memory.memory_chat import memory_chat
from app.memory.vector_store import memory_store
from sqlalchemy.orm import Session

router = APIRouter(prefix="/memory", tags=["memory"])


class MemoryQueryRequest(BaseModel):
    query: str


@router.post("/ask")
def query_meeting_memory(
    payload: MemoryQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Cited Memory Chat Q&A across past and newly completed meeting minutes."""
    results = memory_store.search(query=payload.query, top_k=5, db=db)

    if not results:
        answer = "No matching meeting minutes or decisions were found for this query."
        details = {
            "key_decisions": [],
            "dates": [],
            "owners": [],
            "action_items": [],
            "unavailable": ["No matching meeting records were found."],
        }
        cited_results = []
    else:
        generated = memory_chat(payload.query, db, retrieved_docs=results)
        answer = generated["answer"]
        details = {
            key: generated[key]
            for key in ("key_decisions", "dates", "owners", "action_items", "unavailable")
        }
        cited_ids = set(generated["citations"])
        cited_results = [result for result in results if result["meeting_id"] in cited_ids]

    citations = [
        {
            "meeting_id": result["meeting_id"],
            "title": result["title"],
            "date": result["date"],
            "snippet": result["text"],
        }
        for result in cited_results
    ]

    return {
        "question": payload.query,
        "answer": answer,
        **details,
        "citations": citations,
    }
