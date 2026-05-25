"""add tours, tour_stops, tour_runs

Revision ID: b1f3a2c00001
Revises: 9617f0adc2ab
Create Date: 2026-05-23 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "b1f3a2c00001"
down_revision: Union[str, None] = "9617f0adc2ab"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tours",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name_en", sa.String(100), nullable=False),
        sa.Column("name_ar", sa.String(100), nullable=False),
        sa.Column("name_fr", sa.String(100), nullable=False),
        sa.Column("description_en", sa.Text(), nullable=True),
        sa.Column("description_ar", sa.Text(), nullable=True),
        sa.Column("description_fr", sa.Text(), nullable=True),
        sa.Column("is_preset", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("estimated_minutes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "tour_stops",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id", ondelete="CASCADE"), nullable=False),
        sa.Column("exhibit_id", sa.Integer(), sa.ForeignKey("exhibits.id"), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=False),
    )
    op.create_table(
        "tour_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tour_id", sa.Integer(), sa.ForeignKey("tours.id"), nullable=False),
        sa.Column("current_stop_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="'pending'"),
        sa.Column("language", sa.String(10), nullable=False, server_default="'en'"),
        sa.Column("started_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("tour_runs")
    op.drop_table("tour_stops")
    op.drop_table("tours")
