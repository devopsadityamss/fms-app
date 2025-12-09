"""add missing task fields: notes, updated_at

Revision ID: 20251209_add_task_fields_to_unit_task
Revises: 20251208_add_operation_logging
Create Date: 2025-12-09
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20251209_add_task_fields_to_unit_task"
down_revision = "20251208_add_operation_logging"
branch_labels = None
depends_on = None


def upgrade():
    # NOTE: due_date already exists → do NOT add it again.
    # NOTE: priority already exists → do NOT add it again.

    # Add notes field (NEW)
    op.add_column(
        "unit_tasks",
        sa.Column("notes", sa.Text(), nullable=True)
    )

    # Add updated_at field (NEW)
    op.add_column(
        "unit_tasks",
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"))
    )


def downgrade():
    # Reverse only what this migration added
    op.drop_column("unit_tasks", "updated_at")
    op.drop_column("unit_tasks", "notes")
