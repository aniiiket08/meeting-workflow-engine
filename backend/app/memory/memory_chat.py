import logging
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.core.errors import ValidationFailed
from app.core.logging import setup_logging
from app.memory.vector_store import memory_store
from app.observability.tracer import trace_agent
from app.services.llm import llm_service

logger = setup_logging()


class MemoryChatResponse(BaseModel):
    answer: str = Field(
        min_length=1,
        description="A direct answer to the question, grounded in the meeting records.",
    )
    key_decisions: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    owners: list[str] = Field(default_factory=list)
    action_items: list[str] = Field(default_factory=list)
    unavailable: list[str] = Field(default_factory=list)
    citations: list[int] = Field(
        min_length=1,
        description="IDs of retrieved meetings that support the response.",
    )


@trace_agent(agent_name="memory_chat_agent")
def memory_chat(
    query: str,
    db: Session,
    retrieved_docs: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    """Memory Chat with cited answers and source meeting references."""
    if not query.strip():
        raise ValidationFailed("A meeting-memory question is required.")
    if retrieved_docs is None:
        retrieved_docs = memory_store.search(query=query, top_k=5, db=db)
    if not retrieved_docs:
        raise ValidationFailed("No matching past-meeting context was found.")
    context_str = "\n".join(
        f"- Meeting ID {document['meeting_id']} "
        f"('{document['title']}', {document['date']}): {document['text']}"
        for document in retrieved_docs
    )

    prompt = (
        "Answer the exact question first, using only the supplied meeting records. "
        "Be concise and structured: usually about 100-150 words total, but shorter "
        "for simple factual questions rather than padding. Put relevant information "
        "in the matching fields: key_decisions, dates, owners, and action_items. "
        "Omit irrelevant details and do not repeat the direct answer in the lists. "
        "If requested information is absent from the records, say so in answer and "
        "list it in unavailable; never guess or use outside knowledge. Cite the IDs "
        "of retrieved meetings that support the answer, including records checked "
        "when explaining that a detail is unavailable.\n\n"
        f"Meeting records:\n{context_str}\n\nQuestion: {query}"
    )
    result = llm_service.generate_structured(
        prompt=prompt,
        response_schema=MemoryChatResponse,
        system_prompt=(
            "You answer questions about past meetings. Lead with the exact answer, "
            "use concise factual fields, and ground every claim in supplied records. "
            "Do not invent missing information. Use meeting IDs for citations."
        ),
    )
    allowed_citations = {document["meeting_id"] for document in retrieved_docs}
    invalid_citations = set(result.citations) - allowed_citations
    if invalid_citations or not result.citations:
        logger.warning("Memory Chat returned citations outside retrieved context.")
        raise ValidationFailed("The answer did not cite retrieved meeting context.")
    return result.model_dump()
