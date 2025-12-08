"""create production tables

Revision ID: 001_create_production_tables
Revises:
Create Date: 2025-12-07
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '001_create_production_tables'
down_revision: Union[str, Sequence[str], None] = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- Production Units ---
    op.create_table(
        'production_units',
        sa.Column('id', sa.UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('practice_type', sa.String(), nullable=False),
        sa.Column('category', sa.String(), nullable=True),
        sa.Column('meta', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.Column('health_status', sa.String(), nullable=True),
        sa.Column('start_date', sa.DateTime(), nullable=True),
        sa.Column('end_date', sa.DateTime(), nullable=True),
    )

    op.create_index(
        'ix_production_units_user_id',
        'production_units',
        ['user_id']
    )

    # --- Options ---
    op.create_table(
        'unit_options',
        sa.Column('id', sa.UUID(as_uuid=False), primary_key=True),
        sa.Column('unit_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('option_name', sa.String(), nullable=False),
        sa.Column('meta', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['unit_id'], ['production_units.id'])
    )

    # --- Stages ---
    op.create_table(
        'unit_stages',
        sa.Column('id', sa.UUID(as_uuid=False), primary_key=True),
        sa.Column('unit_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['unit_id'], ['production_units.id'])
    )

    # --- Tasks ---
    op.create_table(
        'unit_tasks',
        sa.Column('id', sa.UUID(as_uuid=False), primary_key=True),
        sa.Column('stage_id', sa.UUID(as_uuid=False), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('completed', sa.Boolean(), nullable=True),
        sa.Column('priority', sa.String(), nullable=True),
        sa.Column('due_date', sa.DateTime(), nullable=True),
        sa.Column('assigned_to', sa.String(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['stage_id'], ['unit_stages.id'])
    )


def downgrade() -> None:
    op.drop_table('unit_tasks')
    op.drop_table('unit_stages')
    op.drop_table('unit_options')
    op.drop_index('ix_production_units_user_id', table_name='production_units')
    op.drop_table('production_units')
