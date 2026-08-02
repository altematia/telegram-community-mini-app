"""Create membership applications table.

Revision ID: 0001
Revises:
Create Date: 2026-08-02
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "applications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("first_name", sa.String(length=80), nullable=False),
        sa.Column("last_name", sa.String(length=80), nullable=False),
        sa.Column("occupation", sa.String(length=160), nullable=False),
        sa.Column("monthly_income", sa.BigInteger(), nullable=False),
        sa.Column("city", sa.String(length=120), nullable=False),
        sa.Column("telegram_user_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_username", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="new", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.CheckConstraint("monthly_income > 0", name="ck_applications_monthly_income_positive"),
    )
    op.create_index("ix_applications_created_at", "applications", ["created_at"])
    op.create_index("ix_applications_status", "applications", ["status"])
    op.create_index("ix_applications_telegram_user_id", "applications", ["telegram_user_id"])


def downgrade() -> None:
    op.drop_index("ix_applications_telegram_user_id", table_name="applications")
    op.drop_index("ix_applications_status", table_name="applications")
    op.drop_index("ix_applications_created_at", table_name="applications")
    op.drop_table("applications")
