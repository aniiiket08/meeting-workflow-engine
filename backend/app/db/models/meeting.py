import enum
from datetime import datetime
from datetime import date
from sqlalchemy import JSON, Date, DateTime, Enum as PyEnum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MeetingStatus(str, enum.Enum):
    REQUESTED = "requested"
    SLOTS_PROPOSED = "slots_proposed"
    SCHEDULED = "scheduled"
    ROOM_BOOKED = "room_booked"
    AGENDA_DRAFTED = "agenda_drafted"
    AGENDA_APPROVED = "agenda_approved"
    IN_PROGRESS = "in_progress"
    TRANSCRIBED = "transcribed"
    MINUTES_DRAFTED = "minutes_drafted"
    MINUTES_APPROVED = "minutes_approved"
    ACTIONS_TRACKED = "actions_tracked"
    DISTRIBUTED = "distributed"
    DISCARDED = "discarded"
    CLOSED = "closed"


class RSVPStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"


class Meeting(Base):
    __tablename__ = "meetings"

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    agenda_items_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    equipment_needed: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    
    organizer_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"), nullable=True)
    zoom_meeting_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    zoom_join_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    status: Mapped[MeetingStatus] = mapped_column(
        PyEnum(MeetingStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=MeetingStatus.REQUESTED,
        nullable=False,
    )

    organizer = relationship("User", foreign_keys=[organizer_id])
    room = relationship("Room", foreign_keys=[room_id])
    attendees = relationship("Attendee", back_populates="meeting", cascade="all, delete-orphan")


class Attendee(Base):
    __tablename__ = "attendees"

    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    external_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    rsvp: Mapped[RSVPStatus] = mapped_column(
        PyEnum(RSVPStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=RSVPStatus.PENDING,
        nullable=False,
    )
    is_priority: Mapped[bool] = mapped_column(default=False, nullable=False)

    meeting = relationship("Meeting", back_populates="attendees")
    user = relationship("User")
