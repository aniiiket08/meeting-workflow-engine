from datetime import datetime, timezone
from typing import Any
import hashlib
from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.agents.follow_up import follow_up_graph
from app.agents.action_tracker import prepare_draft_action_items
from app.agents.minutes import run_minutes_agent
from app.api.deps import get_current_user, get_db, require_meeting_access, require_roles
from app.core.errors import NotFound, ValidationFailed
from app.core.pii import redact_pii
from app.db.models.agenda import Decision
from app.db.models.meeting import Meeting, MeetingStatus
from app.db.models.minutes import Minutes, MinutesStatus, Transcript
from app.db.models.user import User, UserRole
from app.services.stt import stt_service

router = APIRouter(prefix="/meetings", tags=["Minutes"])

class PasteTranscriptRequest(BaseModel):
    text: str

class MinutesUpdateRequest(BaseModel):
    summary: str
    key_discussion_points: list[str]


def _save_minutes_from_transcript(
    db: Session,
    meeting: Meeting,
    transcript: Transcript,
) -> Minutes:
    minutes_dict = run_minutes_agent(
        transcript_text=transcript.redacted_text,
        meeting_id=meeting.id,
    )
    latest_version = (
        db.query(Minutes.version)
        .filter(Minutes.meeting_id == meeting.id)
        .order_by(Minutes.version.desc())
        .scalar()
        or 0
    )
    decisions = minutes_dict["decisions"]
    discussion_points = list(minutes_dict["key_discussion_points"])
    discussion_points.extend(f"Decision: {decision['text']}" for decision in decisions)

    minutes = Minutes(
        meeting_id=meeting.id,
        version=latest_version + 1,
        summary=minutes_dict["summary"],
        key_discussion_points=discussion_points,
        action_items_json=minutes_dict["action_items"],
        status=MinutesStatus.DRAFT,
        content_hash=minutes_dict["content_hash"],
    )
    db.add(minutes)
    db.flush()

    db.query(Decision).filter(Decision.meeting_id == meeting.id).delete()
    db.add_all(
        Decision(
            meeting_id=meeting.id,
            text=decision["text"],
            source_quote=decision["source_quote"],
            timestamp=decision.get("timestamp"),
        )
        for decision in decisions
    )
    db.add_all(
        prepare_draft_action_items(
            db=db,
            meeting_id=meeting.id,
            extracted_actions=minutes_dict["action_items"],
        )
    )
    meeting.status = MeetingStatus.MINUTES_DRAFTED
    db.commit()
    db.refresh(minutes)
    return minutes


def _minutes_response(
    minutes: Minutes,
    transcript: Transcript,
    decisions: list[Decision],
) -> dict[str, Any]:
    action_items = [
        {
            **item,
            "owner_email": item.get("owner_email") or item.get("owner_name"),
            "source_timestamp": item.get("timestamp"),
        }
        for item in minutes.action_items_json
    ]
    return {
        "id": minutes.id,
        "meeting_id": minutes.meeting_id,
        "version": minutes.version,
        "summary": minutes.summary,
        "key_discussion_points": minutes.key_discussion_points,
        "status": minutes.status.value,
        "content_hash": minutes.content_hash,
        "action_items": action_items,
        "decisions": [
            {"text": item.text, "source_quote": item.source_quote, "timestamp": item.timestamp}
            for item in decisions
        ],
        "transcript": transcript.redacted_text,
    }

@router.post("/{meeting_id}/transcript/upload")
def upload_audio_transcript(
    meeting_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.CHAIRMAN, UserRole.PRINCIPAL, UserRole.HOD, UserRole.TEACHER)
    ),
):
    """Upload meeting audio file and transcribe via STT service."""
    audio_bytes = file.file.read()
    if not audio_bytes:
        raise ValidationFailed(message="Uploaded audio file is empty.")

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting is None:
        raise NotFound(entity="Meeting", identifier=meeting_id)
    require_meeting_access(db, meeting, current_user)

    result = stt_service.transcribe(audio_bytes, filename=file.filename)
    redacted = redact_pii(result["text"])

    transcript = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).first()
    if not transcript:
        transcript = Transcript(
            meeting_id=meeting_id,
            raw_text=result["text"],
            redacted_text=redacted,
            language=result["language"],
            content_hash=result["hash"],
        )
        db.add(transcript)
    else:
        transcript.raw_text = result["text"]
        transcript.redacted_text = redacted
        transcript.content_hash = result["hash"]

    meeting.status = MeetingStatus.TRANSCRIBED
    db.commit()
    db.refresh(transcript)
    minutes = _save_minutes_from_transcript(db, meeting, transcript)
    decisions = db.query(Decision).filter(Decision.meeting_id == meeting_id).all()
    return {
        "status": "transcribed",
        "transcript_id": transcript.id,
        "redacted_text": redacted,
        "minutes": _minutes_response(minutes, transcript, decisions),
    }


@router.post("/{meeting_id}/transcript/paste")
def paste_transcript(
    meeting_id: int,
    body: PasteTranscriptRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.CHAIRMAN, UserRole.PRINCIPAL, UserRole.HOD, UserRole.TEACHER)
    ),
):
    """Paste text transcript fallback."""
    if not body.text.strip():
        raise ValidationFailed(message="Transcript text cannot be empty.")

    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting is None:
        raise NotFound(entity="Meeting", identifier=meeting_id)
    require_meeting_access(db, meeting, current_user)

    result = stt_service.process_pasted_transcript(body.text)
    redacted = redact_pii(result["text"])

    transcript = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).first()
    if not transcript:
        transcript = Transcript(
            meeting_id=meeting_id,
            raw_text=result["text"],
            redacted_text=redacted,
            language="en",
            content_hash=result["hash"],
        )
        db.add(transcript)
    else:
        transcript.raw_text = result["text"]
        transcript.redacted_text = redacted
        transcript.content_hash = result["hash"]

    meeting.status = MeetingStatus.TRANSCRIBED
    db.commit()
    db.refresh(transcript)
    minutes = _save_minutes_from_transcript(db, meeting, transcript)
    decisions = db.query(Decision).filter(Decision.meeting_id == meeting_id).all()
    return {
        "status": "processed",
        "transcript_id": transcript.id,
        "redacted_text": redacted,
        "minutes": _minutes_response(minutes, transcript, decisions),
    }


@router.get("/{meeting_id}/minutes")
def get_minutes(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get latest minutes or generate draft from transcript."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting is None:
        raise NotFound(entity="Meeting", identifier=meeting_id)
    require_meeting_access(db, meeting, current_user)
    minutes = db.query(Minutes).filter(Minutes.meeting_id == meeting_id).order_by(Minutes.version.desc()).first()
    transcript = db.query(Transcript).filter(Transcript.meeting_id == meeting_id).first()

    if not minutes:
        if not transcript:
            raise NotFound(entity="Transcript", identifier=meeting_id)
        minutes = _save_minutes_from_transcript(db, meeting, transcript)

    decisions = db.query(Decision).filter(Decision.meeting_id == meeting_id).all()
    return _minutes_response(minutes, transcript, decisions)


@router.post("/{meeting_id}/minutes/approve")
def approve_minutes(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.CHAIRMAN, UserRole.PRINCIPAL)
    ),
):
    """Approve minutes, locking and hashing them (Chairman or Principal only)."""
    minutes = db.query(Minutes).filter(Minutes.meeting_id == meeting_id).order_by(Minutes.version.desc()).first()
    if not minutes:
        raise NotFound(entity="Minutes", identifier=meeting_id)
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting is None:
        raise NotFound(entity="Meeting", identifier=meeting_id)
    require_meeting_access(db, meeting, current_user)

    if minutes.status != MinutesStatus.APPROVED:
        minutes.status = MinutesStatus.APPROVED
        minutes.approved_by_id = current_user.id
        minutes.approved_at = datetime.now(timezone.utc)
        meeting.status = MeetingStatus.MINUTES_APPROVED
        db.commit()

    workflow_result = follow_up_graph.invoke(
        {
            "meeting_id": meeting_id,
            "action_items": minutes.action_items_json,
        },
        config={"configurable": {"db": db}},
    )

    # Index newly approved meeting into MemoryStore for Memory Chat retrieval
    try:
        from app.memory.vector_store import memory_store
        memory_store.sync_from_database(db)
    except Exception:
        pass
    return {
        "status": "approved",
        "minutes_id": minutes.id,
        "content_hash": minutes.content_hash,
        "action_count": len(workflow_result.get("action_ids", [])),
        "distribution_status": workflow_result.get("distribution", {}).get("status"),
        "reminders_sent": workflow_result.get("reminders_sent", 0),
    }
