"""create operation logging tables

Revision ID: 20251208_add_operation_logging
Revises: 77aad1698804
Create Date: 2025-12-08 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "20251208_add_operation_logging"
down_revision = "77aad1698804"
branch_labels = None
depends_on = None


def upgrade():
    # Ensure uuid extension exists
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";')

    # -------------------------------
    # operation_log table
    # -------------------------------
    op.create_table(
        "operation_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("production_unit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("task_template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("performed_on", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="completed"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("reported_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    # Foreign keys
    op.create_foreign_key(
        "fk_operationlog_production_unit",
        "operation_log",
        "production_units",                # corrected
        ["production_unit_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_operationlog_stage",
        "operation_log",
        "unit_stages",                     # corrected
        ["stage_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_operationlog_task_template",
        "operation_log",
        "unit_tasks",                      # corrected
        ["task_template_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_operationlog_reported_by",
        "operation_log",
        "profiles",                        # corrected
        ["reported_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Indexes
    op.create_index("ix_operation_log_production_unit_id", "operation_log", ["production_unit_id"])
    op.create_index("ix_operation_log_performed_on", "operation_log", ["performed_on"])
    op.create_index("ix_operation_log_reported_by_id", "operation_log", ["reported_by_id"])

    # -------------------------------
    # operation_material_usage table
    # -------------------------------
    op.create_table(
        "operation_material_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("operation_log_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_name", sa.String(length=255), nullable=False),
        sa.Column("material_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("unit", sa.String(length=32), nullable=True),
        sa.Column("cost", sa.Float(), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    op.create_foreign_key(
        "fk_material_oplog",
        "operation_material_usage",
        "operation_log",
        ["operation_log_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_material_operation_log_id", "operation_material_usage", ["operation_log_id"])

    # -------------------------------
    # operation_labour_usage table
    # -------------------------------
    op.create_table(
        "operation_labour_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("operation_log_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("worker_name", sa.String(length=255), nullable=True),
        sa.Column("worker_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("hours", sa.Float(), nullable=True),
        sa.Column("labour_cost", sa.Float(), nullable=True),
        sa.Column("role", sa.String(length=128), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    op.create_foreign_key(
        "fk_labour_oplog",
        "operation_labour_usage",
        "operation_log",
        ["operation_log_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index("ix_labour_operation_log_id", "operation_labour_usage", ["operation_log_id"])

    # -------------------------------
    # operation_expense table
    # -------------------------------
    op.create_table(
        "operation_expense",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("operation_log_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("production_unit_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("amount", sa.Float(), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(length=8), nullable=True, server_default="INR"),
        sa.Column("category", sa.String(length=128), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("incurred_on", sa.Date(), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("extra", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    op.create_foreign_key(
        "fk_expense_oplog",
        "operation_expense",
        "operation_log",
        ["operation_log_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_expense_produnit",
        "operation_expense",
        "production_units",                 # corrected
        ["production_unit_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_expense_created_by",
        "operation_expense",
        "profiles",                         # corrected
        ["created_by_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index("ix_operation_expense_produnit_id", "operation_expense", ["production_unit_id"])

    # -------------------------------
    # operation_media table
    # -------------------------------
    op.create_table(
        "operation_media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("operation_log_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_url", sa.Text(), nullable=True),
        sa.Column("mime_type", sa.String(length=128), nullable=True),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    op.create_foreign_key(
        "fk_media_oplog",
        "operation_media",
        "operation_log",
        ["operation_log_id"],
        ["id"],
        ondelete="CASCADE",
    )

    op.create_index("ix_operation_media_oplog_id", "operation_media", ["operation_log_id"])


def downgrade():
    op.drop_index("ix_operation_media_oplog_id", table_name="operation_media")
    op.drop_table("operation_media")

    op.drop_index("ix_operation_expense_produnit_id", table_name="operation_expense")
    op.drop_table("operation_expense")

    op.drop_index("ix_labour_operation_log_id", table_name="operation_labour_usage")
    op.drop_table("operation_labour_usage")

    op.drop_index("ix_material_operation_log_id", table_name="operation_material_usage")
    op.drop_table("operation_material_usage")

    op.drop_index("ix_operation_log_reported_by_id", table_name="operation_log")
    op.drop_index("ix_operation_log_performed_on", table_name="operation_log")
    op.drop_index("ix_operation_log_production_unit_id", table_name="operation_log")
    op.drop_table("operation_log")
