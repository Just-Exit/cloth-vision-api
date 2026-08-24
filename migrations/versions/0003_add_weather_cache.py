"""add shared weather cache

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "weather_cache",
        sa.Column("location_key", sa.String(length=80), nullable=False),
        sa.Column("location", sa.String(length=80), nullable=False),
        sa.Column("provider", sa.String(length=40), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("feels_like", sa.Float(), nullable=False),
        sa.Column("condition", sa.String(length=80), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.Column("precipitation", sa.Float(), nullable=False),
        sa.Column("humidity", sa.Integer(), nullable=False),
        sa.Column("wind_speed", sa.Float(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("location_key", name=op.f("pk_weather_cache")),
    )
    op.create_index(
        op.f("ix_weather_cache_fetched_at"), "weather_cache", ["fetched_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_weather_cache_fetched_at"), table_name="weather_cache")
    op.drop_table("weather_cache")
