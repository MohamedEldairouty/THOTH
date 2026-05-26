"""drop unused media + robot_status tables

robot_status used to persist the robot's last-known pose, but the ROS bridge
already owns that state in-memory, so the table was just a redundant mirror.
The media table was scaffolded but never used (exhibits embed image/audio/
video URLs directly).

Revision ID: c2d4e5f00002
Revises: b1f3a2c00001
Create Date: 2026-05-26 00:00:00
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "c2d4e5f00002"
down_revision: Union[str, None] = "b1f3a2c00001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("media")
    op.drop_table("robot_status")


def downgrade() -> None:
    op.create_table(
        "robot_status",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="idle"),
        sa.Column("battery", sa.Float(), nullable=False, server_default="100.0"),
        sa.Column("current_hall_id", sa.Integer(), sa.ForeignKey("halls.id"), nullable=True),
        sa.Column("current_x", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("current_y", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_table(
        "media",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exhibit_id", sa.Integer(),
                  sa.ForeignKey("exhibits.id", ondelete="CASCADE"), nullable=False),
        sa.Column("media_type", sa.String(50), nullable=False),
        sa.Column("url", sa.String(500), nullable=False),
        sa.Column("caption_en", sa.Text(), nullable=True),
        sa.Column("caption_ar", sa.Text(), nullable=True),
        sa.Column("caption_fr", sa.Text(), nullable=True),
    )
