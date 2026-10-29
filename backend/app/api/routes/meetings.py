from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.agents.room_booking import run_room_booking_agent
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

    meeting.status = MeetingStatus.SLOTS_PROPOSED
    db.commit()
    db.refresh(meeting)

    # Run Scheduling Agent
    slots = run_scheduling_agent(
        attendee_emails=all_emails,
        duration_minutes=payload.duration_minutes,
        target_date_iso=payload.target_date.isoformat() if payload.target_date else None,
        meeting_id=meeting.id,
    )

    return {
        "meeting": MeetingResponse.model_validate(meeting),
        "slots": slots,
    }


@router.get("", response_model=list[MeetingResponse])
def list_meetings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Meeting]:
    """List all meetings in the system."""
    return visible_meetings_query(db, current_user).order_by(Meeting.created_at.desc()).all()


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

    # When user chooses an online meeting via Zoom MCP:
    if payload.is_online:
        from dateutil.parser import parse as parse_date
        from mcp_server.server import MCPServerSkeleton
        mcp = MCPServerSkeleton()
        
        # Calculate start/end dt
        start_dt = parse_date(payload.selected_start_time)
        end_dt = parse_date(payload.selected_end_time)
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
            
        duration = max(15, int((end_dt - start_dt).total_seconds() // 60))
        zoom_res = mcp.call_tool(
            "zoom_create_meeting",
            {
                "topic": meeting.title,
                "start_time": start_dt.isoformat(),
                "duration_minutes": duration,
                "timezone": "UTC",
                "idempotency_key": f"meeting_{meeting.id}_{start_dt.isoformat()}",
            },
            agent_name="scheduling_agent",
        )
        meeting.start_time = start_dt
        meeting.end_time = end_dt
        meeting.room_id = None
        meeting.zoom_meeting_id = str(zoom_res.get("id"))
        meeting.zoom_join_url = zoom_res.get("join_url")
        meeting.status = MeetingStatus.ROOM_BOOKED  # Time & venue confirmed
        db.commit()
        db.refresh(meeting)
        return {
            "meeting": MeetingResponse.model_validate(meeting),
            "room_booking": {
                "status": "online",
                "message": "Zoom Online Meeting successfully scheduled.",
                "zoom": zoom_res,
            },
        }

    headcount = len(meeting.attendees) if meeting.attendees else 1

    # Run Room Booking Agent — pass an explicit room_id when the user selected one.
    booking_result = run_room_booking_agent(
        db=db,
        meeting_id=meeting.id,
        headcount=headcount,
        start_time_iso=payload.selected_start_time,
        end_time_iso=payload.selected_end_time,
        equipment_needed=meeting.equipment_needed,
        room_id=payload.room_id,
    )

    db.refresh(meeting)
    return {
        "meeting": MeetingResponse.model_validate(meeting),
        "room_booking": booking_result,
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

