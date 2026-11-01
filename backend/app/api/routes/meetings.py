from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.scheduling import run_scheduling_agent
from app.api.deps import (
    get_current_user,
    get_db,
    is_meeting_manager,
    require_meeting_access,
    require_roles,
    visible_meetings_query,
)
from app.core.errors import NotFound
from app.db.models.meeting import Attendee, Meeting, MeetingStatus
from app.db.models.user import User, UserRole
from app.db.schemas.meeting import MeetingConfirmRequest, MeetingCreate, MeetingResponse, SlotOption
from app.services.job_worker import enqueue_job

router = APIRouter(prefix="/meetings", tags=["meetings"])


@router.post("", response_model=dict[str, Any])
def create_meeting_request(
    payload: MeetingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.CHAIRMAN,
            UserRole.PRINCIPAL,
            UserRole.HOD,
            UserRole.TEACHER,
        )
    ),
) -> dict[str, Any]:
    """Create a meeting request and generate 3 ranked slots."""
    meeting = Meeting(
        title=payload.title,
        description=payload.description,
        agenda_items_text=payload.agenda_items_text or None,
        duration_minutes=payload.duration_minutes,
        target_date=payload.target_date,
        equipment_needed=payload.equipment_needed,
        organizer_id=current_user.id,
        status=MeetingStatus.REQUESTED,
    )
    db.add(meeting)
    db.flush()

    # Link attendees
    all_emails = sorted(
        {str(email).strip().lower() for email in payload.attendee_emails}
        | {current_user.email.strip().lower()}
    )
    for email in all_emails:
        user = db.query(User).filter(func.lower(User.email) == email).first()
        if user:
            db.add(Attendee(meeting_id=meeting.id, user_id=user.id))
        elif email != current_user.email.lower():
            db.add(Attendee(meeting_id=meeting.id, external_email=email))

    meeting.status = MeetingStatus.REQUESTED
    db.flush()
    job = enqueue_job(
        db,
        "meeting_start",
        current_user.id,
        {
            "attendee_emails": all_emails,
            "duration_minutes": payload.duration_minutes,
            "target_date_iso": payload.target_date.isoformat() if payload.target_date else None,
            "meeting_id": meeting.id,
        },
        "Finding meeting times...",
        meeting_id=meeting.id,
    )
    db.refresh(meeting)

    return {
        "meeting": MeetingResponse.model_validate(meeting),
        "job_id": job.id,
        "status": job.status,
        "progress_text": job.progress_text,
    }


@router.get("", response_model=list[MeetingResponse])
def list_meetings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Meeting]:
    """List all meetings in the system."""
    return visible_meetings_query(db, current_user).order_by(Meeting.created_at.desc()).all()


@router.get("/{meeting_id}", response_model=MeetingResponse)
def get_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Meeting:
    """Retrieve one meeting visible to the authenticated user."""
    meeting = (
        visible_meetings_query(db, current_user)
        .filter(Meeting.id == meeting_id)
        .first()
    )
    if meeting is None:
        raise NotFound(entity="Meeting", identifier=meeting_id)
    return meeting


@router.get("/{meeting_id}/slots", response_model=list[SlotOption])
def get_meeting_slots(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Retrieve ranked candidate slots for a meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise NotFound(entity="Meeting", identifier=meeting_id)
    require_meeting_access(db, meeting, current_user)

    attendee_emails = [
        a.user.email if a.user else a.external_email
        for a in meeting.attendees
        if a.user or a.external_email
    ]
    if not attendee_emails:
        attendee_emails = [current_user.email]

    slots = run_scheduling_agent(
        attendee_emails=attendee_emails,
        duration_minutes=meeting.duration_minutes,
        target_date_iso=meeting.target_date.isoformat() if meeting.target_date else None,
        meeting_id=meeting.id,
    )
    return slots


@router.post("/{meeting_id}/confirm", response_model=dict[str, Any])
def confirm_meeting_slot(
    meeting_id: int,
    payload: MeetingConfirmRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Confirm a slot and trigger room booking agent."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise NotFound(entity="Meeting", identifier=meeting_id)
    require_meeting_access(db, meeting, current_user)
    if not is_meeting_manager(current_user) and meeting.organizer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the meeting organizer or a university manager can confirm its time.",
        )

    headcount = len(meeting.attendees) if meeting.attendees else 1
    job = enqueue_job(
        db,
        "meeting_confirm",
        current_user.id,
        {
            "is_online": payload.is_online,
            "selected_start_time": payload.selected_start_time,
            "selected_end_time": payload.selected_end_time,
            "headcount": headcount,
            "equipment_needed": meeting.equipment_needed or [],
            "room_id": payload.room_id,
        },
        "Confirming meeting time and venue...",
        meeting_id=meeting.id,
    )
    return {
        "meeting": MeetingResponse.model_validate(meeting),
        "job_id": job.id,
        "status": job.status,
        "progress_text": job.progress_text,
    }


@router.post("/{meeting_id}/discard", response_model=MeetingResponse)
def discard_meeting(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.CHAIRMAN, UserRole.PRINCIPAL, UserRole.HOD)
    ),
) -> Meeting:
    """Discard a meeting. Accessible to Chairman, Principal, and HOD."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise NotFound(entity="Meeting", identifier=meeting_id)

    meeting.status = MeetingStatus.DISCARDED
    db.commit()
    db.refresh(meeting)
    return meeting
