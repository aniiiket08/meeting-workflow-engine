from datetime import date, datetime, timezone
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.db.models.meeting import MeetingStatus, RSVPStatus


class MeetingCreate(BaseModel):
    title: str
    description: str | None = None
    agenda_items_text: str | None = Field(
        default=None,
        description=(
            "Optional agenda items, one per line. "
            "Format: Title [ | Lead, Lead2 ] [ | minutes ]. "
            "Example: Live demo | Aniket, Sujal | 15"
        ),
    )
    duration_minutes: int = Field(default=60, ge=15, le=480)
    target_date: date | None = None
    attendee_emails: list[EmailStr] = Field(default_factory=list)
    equipment_needed: list[str] = Field(default_factory=list)


class SlotOption(BaseModel):
    slot_index: int
    start_time: str
    end_time: str
    score: float
    reason: str
    conflicts: list[str]


class MeetingConfirmRequest(BaseModel):
    selected_start_time: str
    selected_end_time: str
    room_id: int | None = None
    is_online: bool = False


class MeetingResponse(BaseModel):
    id: int
    title: str
    description: str | None
    agenda_items_text: str | None
    duration_minutes: int
    target_date: date | None
    equipment_needed: list[str]
    start_time: datetime | None
    end_time: datetime | None
    organizer_id: int
    room_id: int | None
    zoom_meeting_id: str | None = None
    zoom_join_url: str | None = None
    status: MeetingStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

    @field_validator("start_time", "end_time")
    @classmethod
    def mark_naive_times_as_utc(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
