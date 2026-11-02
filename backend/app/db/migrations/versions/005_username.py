"""add username column to users

Revision ID: 005_username
Revises: 004_transcripts_and_minutes
Create Date: 2026-10-05 12:30:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_username"
down_revision: Union[str, None] = "004_transcripts_and_minutes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add a unique, indexed ``username`` column and backfill from email."""
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("username", sa.String(length=64), nullable=True))

    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        local_part = "split_part(email, '@', 1)"
    elif dialect == "sqlite":
        local_part = "substr(email, 1, instr(email, '@') - 1)"
    else:
        raise RuntimeError(f"Username backfill is unsupported for database dialect {dialect!r}.")

    op.execute(
        "UPDATE users "
        f"SET username = {local_part} "
        "WHERE username IS NULL OR username = ''"
    )

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("username", existing_type=sa.String(length=64), nullable=False)
        batch_op.create_index(op.f("ix_users_username"), ["username"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index(op.f("ix_users_username"))
        batch_op.drop_column("username")