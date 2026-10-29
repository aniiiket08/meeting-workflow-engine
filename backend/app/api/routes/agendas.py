from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.agents.agenda import run_agenda_agent
from app.api.deps import get_current_user, get_db, is_meeting_manager, require_meeting_access, require_roles
from app.core.errors import Conflict, NotFound
from app.db.models.agenda import Agenda, AgendaStatus
from app.db.models.meeting import Meeting, MeetingStatus
from app.db.models.user import User, UserRole

router = APIRouter(tags=["agendas"])


class AgendaUpdateRequest(BaseModel):
    items: list[dict[str, Any]]


@router.get("/meetings/{meeting_id}/agenda")
def get_meeting_agenda(
    meeting_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get or generate draft agenda for a meeting."""
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise NotFound(entity="Meeting", identifier=meeting_id)
    require_meeting_access(db, meeting, current_user)

    db_agenda = db.query(Agenda).filter(Agenda.meeting_id == meeting_id).first()
    if not db_agenda:
        if not is_meeting_manager(current_user):
            raise NotFound(entity="Agenda for Meeting", identifier=meeting_id)
        agenda_model = run_agenda_agent(
            db=db,
            meeting_id=meeting_id,
            agenda_items_text=meeting.agenda_items_text or None,
        )
        db_agenda = Agenda(
            meeting_id=meeting_id,
            items_json=[item.model_dump() for item in agenda_model.items],
            status=AgendaStatus.DRAFT,
        )
        db.add(db_agenda)
        meeting.status = MeetingStatus.AGENDA_DRAFTED
        db.commit()
        db.refresh(db_agenda)

    return {
        "id": db_agenda.id,
        "meeting_id": db_agenda.meeting_id,
        "items": db_agenda.items_json,
        "status": db_agenda.status.value,
        "approved_at": db_agenda.approved_at,
        "meeting_title": meeting.title,
        "duration_minutes": meeting.duration_minutes,
        "agenda_items_text": meeting.agenda_items_text,
    }


@router.put("/meetings/{meeting_id}/agenda")
def update_meeting_agenda(
    meeting_id: int,
    payload: AgendaUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_roles(UserRole.CHAIRMAN, UserRole.PRINCIPAL, UserRole.HOD)
    ),
) -> dict[str, Any]:
    """Update draft agenda items."""
    db_agenda = db.query(Agenda).filter(Agenda.meeting_id == meeting_id).first()
    if not db_agenda:
        raise NotFound(entity="Agenda for Meeting", identifier=meeting_id)
    if db_agenda.status == AgendaStatus.APPROVED:
        raise Conflict("Approved agendas are locked.", action="create_a_new_agenda_version")

    db_agenda.items_json = payload.items
    db.commit()
    db.refresh(db_agenda)
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    return {
        "id": db_agenda.id,
        "meeting_id": db_agenda.meeting_id,
        "items": db_agenda.items_json,
        "status": db_agenda.status.value,
        "approved_at": db_agenda.approved_at,
        "meeting_title": meeting.title if meeting else "Meeting",
        "duration_minutes": meeting.duration_minutes if meeting else 0,
    }


@router.post("/agendas/{agenda_id}/approve")
def approve_agenda(
    agenda_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.CHAIRMAN)),
) -> dict[str, Any]:
    """Human Approval Gate: Approve meeting agenda (Chairman only)."""
    db_agenda = db.query(Agenda).filter(Agenda.id == agenda_id).first()
    if not db_agenda:
        raise NotFound(entity="Agenda", identifier=agenda_id)

    db_agenda.status = AgendaStatus.APPROVED
    db_agenda.approved_by_id = current_user.id
    db_agenda.approved_at = datetime.now(timezone.utc)

    # Update meeting status
    meeting = db.query(Meeting).filter(Meeting.id == db_agenda.meeting_id).first()
    if meeting:
        meeting.status = MeetingStatus.AGENDA_APPROVED

    db.commit()
    return {
        "id": db_agenda.id,
        "meeting_id": db_agenda.meeting_id,
        "items": db_agenda.items_json,
        "status": db_agenda.status.value,
        "approved_at": db_agenda.approved_at,
        "meeting_title": meeting.title if meeting else "Meeting",
        "duration_minutes": meeting.duration_minutes if meeting else 0,
    }
