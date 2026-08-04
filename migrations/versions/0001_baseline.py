"""Capture the pre-Alembic four-table schema.

Revision ID: 0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("nickname", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "auth_identities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=30), nullable=False),
        sa.Column("subject", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_auth_identities_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_auth_identities"),
        sa.UniqueConstraint("provider", "subject", name="uq_auth_identity_provider_subject"),
    )
    op.create_index("ix_auth_identities_provider", "auth_identities", ["provider"], unique=False)
    op.create_index("ix_auth_identities_user_id", "auth_identities", ["user_id"], unique=False)

    op.create_table(
        "closets",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_closets_user_id_users"),
        sa.PrimaryKeyConstraint("id", name="pk_closets"),
    )
    op.create_index("ix_closets_user_id", "closets", ["user_id"], unique=False)

    op.create_table(
        "items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("closet_id", sa.String(length=36), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("subcategory", sa.String(length=60), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("image_key", sa.String(length=255), nullable=True),
        sa.Column("color_hex", sa.String(length=7), nullable=True),
        sa.Column("color_name", sa.String(length=50), nullable=True),
        sa.Column("style_tags", sa.JSON(), nullable=False),
        sa.Column("season_tags", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("user_attributes", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["closet_id"], ["closets.id"], name="fk_items_closet_id_closets"),
        sa.PrimaryKeyConstraint("id", name="pk_items"),
    )
    op.create_index("ix_items_closet_id", "items", ["closet_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_items_closet_id", table_name="items")
    op.drop_table("items")
    op.drop_index("ix_closets_user_id", table_name="closets")
    op.drop_table("closets")
    op.drop_index("ix_auth_identities_user_id", table_name="auth_identities")
    op.drop_index("ix_auth_identities_provider", table_name="auth_identities")
    op.drop_table("auth_identities")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
