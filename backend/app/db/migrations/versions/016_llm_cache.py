"""Create the LLM cache table through Alembic.

Revision ID: 016_llm_cache
Revises: 015_reminder_delivery_state
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import context, op

revision: str = "016_llm_cache"
down_revision: Union[str, None] = "015_reminder_delivery_state"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not context.is_offline_mode() and sa.inspect(op.get_bind()).has_table("llm_cache"):
        return

    op.create_table(
        "llm_cache",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("prompt_hash", sa.String(length=64), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_llm_cache_id", "llm_cache", ["id"], unique=False)
    op.create_index(
        "ix_llm_cache_prompt_hash",
        "llm_cache",
        ["prompt_hash"],
        unique=True,
    )


def downgrade() -> None:
    # This table predates this revision in some databases and may contain cache data.
    return
