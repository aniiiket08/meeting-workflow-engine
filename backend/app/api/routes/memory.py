from typing import Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.deps import get_current_user, get_db
from app.db.models.user import User
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
    results = memory_store.search(query=payload.query, top_k=3, db=db)

    citations = [
        {
            "meeting_id": r["meeting_id"],
            "title": r["title"],
            "date": r["date"],
            "snippet": r["text"],
        }
        for r in results
    ]

    if not results:
        answer = "No matching meeting minutes or decisions were found for this query."
    else:
        # Provide cited answer grounded in the matching meeting documentation
        lead_doc = results[0]
        answer = f"Based on meeting '{lead_doc['title']}' ({lead_doc['date']}): {lead_doc['text']}"

    return {
        "question": payload.query,
        "answer": answer,
        "citations": citations,
    }
