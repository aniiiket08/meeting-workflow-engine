import enum
from datetime import datetime
from sqlalchemy import DateTime, Enum as PyEnum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ActionStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ActionPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ActionItem(Base):
    __tablename__ = "action_items"

    meeting_id: Mapped[int] = mapped_column(ForeignKey("meetings.id"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True, index=True)
    owner_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    
    priority: Mapped[ActionPriority] = mapped_column(
        PyEnum(ActionPriority, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=ActionPriority.MEDIUM,
        nullable=False,
    )
    status: Mapped[ActionStatus] = mapped_column(
        PyEnum(ActionStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=ActionStatus.PENDING,
        nullable=False,
        index=True,
    )
    
    source_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_timestamp: Mapped[str | None] = mapped_column(String(20), nullable=True)
    needs_confirmation: Mapped[bool] = mapped_column(default=False, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    meeting = relationship("Meeting")
    owner = relationship("User")
