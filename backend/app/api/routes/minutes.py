from datetime import datetime, timezone
from typing import Any
import base64
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.agents.action_tracker import prepare_draft_action_items
from app.agents.minutes import run_minutes_agent
from app.api.deps import get_current_user, get_db, require_meeting_access, require_roles
from app.core.errors import NotFound, ValidationFailed
from app.db.models.agenda import Decision
from app.db.models.meeting import Meeting, MeetingStatus
from app.db.models.minutes import Minutes, MinutesStatus, Transcript
from app.db.models.user import User, UserRole
from app.services.job_worker import enqueue_job
from app.db.models.job import Job
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
    commit: bool = True,
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
    if commit:
        db.commit()
        db.refresh(minutes)
    else:
        db.flush()
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

    job = enqueue_job(
        db,
        "transcript_upload",
        current_user.id,
        {
            "audio_base64": base64.b64encode(audio_bytes).decode("ascii"),
            "filename": file.filename,
        },
        "Transcribing audio...",
        meeting_id=meeting_id,
    )
    return {"job_id": job.id, "status": job.status, "progress_text": job.progress_text}


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

    job = enqueue_job(
        db,
        "transcript_paste",
        current_user.id,
        {"text": body.text},
        "Extracting tasks...",
        meeting_id=meeting_id,
    )
    return {"job_id": job.id, "status": job.status, "progress_text": job.progress_text}


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
        job = enqueue_job(
            db,
            "minutes_draft",
            current_user.id,
            {},
            "Drafting minutes...",
            meeting_id=meeting_id,
        )
        return {"job_id": job.id, "status": job.status, "progress_text": job.progress_text}

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

    active_job = (
        db.query(Job)
        .filter(
            Job.type == "minutes_approve",
            Job.meeting_id == meeting_id,
            Job.status.in_(["pending", "running"]),
        )
        .order_by(Job.created_at.desc())
        .first()
    )
    job = active_job or enqueue_job(
        db,
        "minutes_approve",
        current_user.id,
        {"minutes_id": minutes.id},
        "Creating follow-up tasks...",
        meeting_id=meeting_id,
    )
    return {
        "status": "approved",
        "minutes_id": minutes.id,
        "content_hash": minutes.content_hash,
        "job_id": job.id,
        "job_status": job.status,
        "progress_text": job.progress_text,
    }


@router.post("/{meeting_id}/minutes/distribute")
def distribute_minutes(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CHAIRMAN, UserRole.PRINCIPAL)),
):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting is None:
        raise NotFound(entity="Meeting", identifier=meeting_id)
    require_meeting_access(db, meeting, current_user)
    minutes = (
        db.query(Minutes)
        .filter(Minutes.meeting_id == meeting_id)
        .order_by(Minutes.version.desc())
        .first()
    )
    if minutes is None or minutes.status != MinutesStatus.APPROVED:
        raise ValidationFailed("Minutes must be approved before distribution.")
    job = enqueue_job(
        db,
        "minutes_distribute",
        current_user.id,
        {},
        "Distributing approved minutes...",
        meeting_id=meeting_id,
    )
    return {"job_id": job.id, "status": job.status, "progress_text": job.progress_text}
