"""Track reminder delivery attempt state for safe retry handling.

Revision ID: 015_reminder_delivery_state
Revises: 014_background_jobs
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "015_reminder_delivery_state"
down_revision: Union[str, None] = "014_background_jobs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("sent_reminders") as batch_op:
        batch_op.add_column(
            sa.Column("status", sa.String(length=20), nullable=False, server_default="sent")
        )


def downgrade() -> None:
    with op.batch_alter_table("sent_reminders") as batch_op:
        batch_op.drop_column("status")
