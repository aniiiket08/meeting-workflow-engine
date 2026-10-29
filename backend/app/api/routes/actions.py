from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from sqlalchemy import func, or_

from app.api.deps import get_current_user, get_db, is_meeting_manager
from app.core.errors import NotFound
from app.db.models.action import ActionItem, ActionStatus, ActionPriority
from app.db.models.user import User, UserRole

router = APIRouter(prefix="/actions", tags=["Actions"])

class ActionItemResponse(BaseModel):
    id: int
    meeting_id: int
    description: str
    owner_id: int | None
    owner_name: Optional[str]
    owner_email: Optional[str]
    due_date: Optional[str]
    priority: str
    status: str
    confidence: float
    source_quote: Optional[str]
    source_timestamp: Optional[str]
    needs_confirmation: bool

class ActionStatusUpdate(BaseModel):
    status: ActionStatus

class ActionAssignRequest(BaseModel):
    user_id: int | None = Field(None, alias="owner_id")

    model_config = {"populate_by_name": True}

@router.get("", response_model=List[ActionItemResponse])
def list_action_items(
    status: Optional[ActionStatus] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List action items with optional status filtering."""
    query = db.query(ActionItem)
    if current_user.role in {UserRole.TEACHER, UserRole.STUDENT}:
        query = query.filter(
            or_(
                ActionItem.owner_id == current_user.id,
                func.lower(ActionItem.owner_email) == current_user.email.lower(),
            )
        )
    if status:
        query = query.filter(ActionItem.status == status)

    items = query.order_by(ActionItem.created_at.desc()).all()
    res = []
    for i in items:
        res.append(
            ActionItemResponse(
                id=i.id,
                meeting_id=i.meeting_id,
                description=i.description,
                owner_id=i.owner_id,
                owner_name=i.owner.name if i.owner else i.owner_name or "Unassigned",
                owner_email=i.owner.email if i.owner else i.owner_email,
                due_date=i.due_date.strftime("%Y-%m-%d") if i.due_date else None,
                priority=i.priority.value,
                status=i.status.value,
                confidence=i.confidence or 0.9,
                source_quote=i.source_quote,
                source_timestamp=i.source_timestamp,
                needs_confirmation=i.needs_confirmation,
            )
        )
    return res


@router.put("/{action_id}/assign", response_model=ActionItemResponse)
def assign_action_item(
    action_id: int,
    body: ActionAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Assign an action item to a university member."""
    if not is_meeting_manager(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Chairman, Principal, and HOD can assign action items.",
        )
    item = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not item:
        raise NotFound(entity="ActionItem", identifier=action_id)

    owner = None
    if body.user_id is not None:
        owner = db.query(User).filter(User.id == body.user_id).first()
        if owner is None:
            raise NotFound(entity="User", identifier=body.user_id)
        if current_user.role == UserRole.HOD and owner.role not in {
            UserRole.TEACHER,
            UserRole.STUDENT,
        }:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HOD can assign department tasks to Teachers and Students.",
            )

    item.owner_id = owner.id if owner else None
    item.owner_name = owner.name if owner else None
    item.owner_email = owner.email if owner else None
    item.needs_confirmation = owner is None
    db.commit()
    db.refresh(item)
    return ActionItemResponse(
        id=item.id,
        meeting_id=item.meeting_id,
        description=item.description,
        owner_id=item.owner_id,
        owner_name=item.owner.name if item.owner else item.owner_name or "Unassigned",
        owner_email=item.owner.email if item.owner else item.owner_email,
        due_date=item.due_date.strftime("%Y-%m-%d") if item.due_date else None,
        priority=item.priority.value,
        status=item.status.value,
        confidence=item.confidence or 0.9,
        source_quote=item.source_quote,
        source_timestamp=item.source_timestamp,
        needs_confirmation=item.needs_confirmation,
    )


@router.put("/{action_id}/status", response_model=ActionItemResponse)
def update_action_status(
    action_id: int,
    body: ActionStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update action item status (Pending, In Progress, Completed)."""
    item = db.query(ActionItem).filter(ActionItem.id == action_id).first()
    if not item:
        raise NotFound(entity="ActionItem", identifier=action_id)
    is_owner = item.owner_id == current_user.id or (
        item.owner_email is not None
        and item.owner_email.lower() == current_user.email.lower()
    )
    if not is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update the status of action items assigned to you.",
        )

    item.status = body.status
    db.commit()
    db.refresh(item)

    return ActionItemResponse(
        id=item.id,
        meeting_id=item.meeting_id,
        description=item.description,
        owner_id=item.owner_id,
        owner_name=item.owner.name if item.owner else item.owner_name or "Unassigned",
        owner_email=item.owner.email if item.owner else item.owner_email,
        due_date=item.due_date.strftime("%Y-%m-%d") if item.due_date else None,
        priority=item.priority.value,
        status=item.status.value,
        confidence=item.confidence or 0.9,
        source_quote=item.source_quote,
        source_timestamp=item.source_timestamp,
        needs_confirmation=item.needs_confirmation,
    )
