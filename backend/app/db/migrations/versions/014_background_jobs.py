"""Add persistent background jobs.

Revision ID: 014_background_jobs
Revises: 013_meeting_agenda_items_text
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "014_background_jobs"
down_revision: Union[str, None] = "013_meeting_agenda_items_text"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("progress_text", sa.String(length=200), nullable=False),
        sa.Column("result_ref", sa.String(length=255), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("meeting_id", sa.Integer(), sa.ForeignKey("meetings.id"), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_jobs_type", "jobs", ["type"])
    op.create_index("ix_jobs_status", "jobs", ["status"])
    op.create_index("ix_jobs_user_id", "jobs", ["user_id"])
    op.create_index("ix_jobs_meeting_id", "jobs", ["meeting_id"])


def downgrade() -> None:
    op.drop_index("ix_jobs_meeting_id", table_name="jobs")
    op.drop_index("ix_jobs_user_id", table_name="jobs")
    op.drop_index("ix_jobs_status", table_name="jobs")
    op.drop_index("ix_jobs_type", table_name="jobs")
    op.drop_table("jobs")
