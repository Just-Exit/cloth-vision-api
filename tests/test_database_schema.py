from __future__ import annotations

import os
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    MetaData,
    String,
    Table,
    UniqueConstraint,
    inspect,
    text,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import configure_mappers

from cloth_vision_api.adapters.outbound.database import (
    Base,
    downgrade_database,
    upgrade_database,
    verify_database_schema,
)
from cloth_vision_api.adapters.outbound.database.repository import create_database_engine

EXPECTED_TABLES = {
    "analysis_jobs",
    "auth_identities",
    "closets",
    "import_jobs",
    "item_analyses",
    "item_images",
    "items",
    "outfit_feedback",
    "outfit_items",
    "outfit_reviews",
    "outfits",
    "refresh_tokens",
    "subscriptions",
    "user_preferences",
    "user_profiles",
    "users",
    "wear_events",
}


def sqlite_url(tmp_path, name: str = "schema.db") -> str:
    return f"sqlite:///{tmp_path / name}"


def constraint_names(table_name: str) -> set[str]:
    return {constraint.name for constraint in Base.metadata.tables[table_name].constraints}


def create_legacy_create_all_schema(database_url: str) -> None:
    """Reproduce the metadata contract used before Alembic was introduced."""
    metadata = MetaData()
    users = Table(
        "users",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("email", String(320), nullable=False),
        Column("nickname", String(80), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )
    Index("ix_users_email", users.c.email, unique=True)
    auth_identities = Table(
        "auth_identities",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("user_id", ForeignKey("users.id"), nullable=False),
        Column("provider", String(30), nullable=False),
        Column("subject", String(320), nullable=False),
        Column("password_hash", String(255), nullable=True),
        Column("created_at", DateTime(timezone=True), nullable=False),
        UniqueConstraint("provider", "subject", name="uq_auth_identity_provider_subject"),
    )
    Index("ix_auth_identities_user_id", auth_identities.c.user_id)
    Index("ix_auth_identities_provider", auth_identities.c.provider)
    closets = Table(
        "closets",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("user_id", ForeignKey("users.id"), nullable=False),
        Column("name", String(80), nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
    )
    Index("ix_closets_user_id", closets.c.user_id)
    items = Table(
        "items",
        metadata,
        Column("id", String(36), primary_key=True),
        Column("closet_id", ForeignKey("closets.id"), nullable=False),
        Column("display_name", String(120), nullable=False),
        Column("category", String(30), nullable=False),
        Column("subcategory", String(60), nullable=True),
        Column("status", String(30), nullable=False),
        Column("image_key", String(255), nullable=True),
        Column("color_hex", String(7), nullable=True),
        Column("color_name", String(50), nullable=True),
        Column("style_tags", JSON, nullable=False),
        Column("season_tags", JSON, nullable=False),
        Column("confidence", Float, nullable=True),
        Column("user_attributes", JSON, nullable=False),
        Column("created_at", DateTime(timezone=True), nullable=False),
        Column("updated_at", DateTime(timezone=True), nullable=False),
    )
    Index("ix_items_closet_id", items.c.closet_id)

    engine = create_database_engine(database_url)
    metadata.create_all(engine)
    engine.dispose()


def seed_legacy_data(database_url: str) -> tuple[str, str, str]:
    user_id = str(uuid4())
    closet_id = str(uuid4())
    item_id = str(uuid4())
    now = datetime.now(UTC)
    engine = create_database_engine(database_url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, email, nickname, created_at) "
                "VALUES (:id, :email, :nickname, :created_at)"
            ),
            {
                "id": user_id,
                "email": f"legacy-{user_id}@example.com",
                "nickname": "legacy",
                "created_at": now,
            },
        )
        connection.execute(
            text(
                "INSERT INTO closets (id, user_id, name, created_at) "
                "VALUES (:id, :user_id, :name, :created_at)"
            ),
            {"id": closet_id, "user_id": user_id, "name": "내 옷장", "created_at": now},
        )
        connection.execute(
            text(
                "INSERT INTO items "
                "(id, closet_id, display_name, category, status, style_tags, season_tags, "
                "user_attributes, created_at, updated_at) "
                "VALUES (:id, :closet_id, :display_name, :category, :status, '[]', '[]', "
                "'{}', :created_at, :updated_at)"
            ),
            {
                "id": item_id,
                "closet_id": closet_id,
                "display_name": "기존 재킷",
                "category": "outer",
                "status": "ready",
                "created_at": now,
                "updated_at": now,
            },
        )
    engine.dispose()
    return user_id, closet_id, item_id


def assert_legacy_data_survived(
    database_url: str, user_id: str, closet_id: str, item_id: str
) -> None:
    engine = create_database_engine(database_url)
    with engine.connect() as connection:
        item = connection.execute(
            text(
                "SELECT analysis_status, lifecycle_status, source_type, wear_count "
                "FROM items WHERE id = :id"
            ),
            {"id": item_id},
        ).one()
        user_status = connection.execute(
            text("SELECT status FROM users WHERE id = :id"), {"id": user_id}
        ).scalar_one()
        closet_default = connection.execute(
            text("SELECT is_default FROM closets WHERE id = :id"), {"id": closet_id}
        ).scalar_one()

    assert tuple(item) == ("ready", "active", "manual", 0)
    assert user_status == "active"
    assert closet_default in (False, 0)
    engine.dispose()


def test_orm_metadata_matches_wireframe_domain_contract() -> None:
    configure_mappers()

    assert set(Base.metadata.tables) == EXPECTED_TABLES
    assert {
        "analysis_status",
        "lifecycle_status",
        "source_type",
        "materials",
        "colors",
        "wear_count",
    } <= set(Base.metadata.tables["items"].columns.keys())
    assert "status" not in Base.metadata.tables["items"].columns.keys()

    assert "ck_items_valid_analysis_status" in constraint_names("items")
    assert "ck_items_valid_lifecycle_status" in constraint_names("items")
    assert "uq_outfit_feedback_user_outfit" in constraint_names("outfit_feedback")
    assert "uq_wear_events_user_idempotency" in constraint_names("wear_events")
    assert "ck_outfit_reviews_valid_rating" in constraint_names("outfit_reviews")

    outfit_item_fk_actions = {
        foreign_key.ondelete
        for foreign_key in Base.metadata.tables["outfit_items"].foreign_key_constraints
    }
    assert outfit_item_fk_actions == {"CASCADE", "RESTRICT"}


def test_alembic_head_matches_orm_metadata(tmp_path) -> None:
    database_url = sqlite_url(tmp_path)
    upgrade_database(database_url)

    engine = create_database_engine(database_url)
    actual_tables = set(inspect(engine).get_table_names()) - {"alembic_version"}
    assert actual_tables == EXPECTED_TABLES
    assert {column["name"] for column in inspect(engine).get_columns("items")} >= {
        "analysis_status",
        "lifecycle_status",
        "source_type",
        "materials",
        "colors",
        "wear_count",
    }
    assert "status" not in {column["name"] for column in inspect(engine).get_columns("items")}

    verify_database_schema(database_url)
    engine.dispose()


def test_baseline_data_survives_expansion_migration(tmp_path) -> None:
    database_url = sqlite_url(tmp_path)
    create_legacy_create_all_schema(database_url)
    user_id, closet_id, item_id = seed_legacy_data(database_url)

    upgrade_database(database_url)
    assert_legacy_data_survived(database_url, user_id, closet_id, item_id)


def test_database_constraints_reject_invalid_profile_values(tmp_path) -> None:
    database_url = sqlite_url(tmp_path)
    upgrade_database(database_url)
    engine = create_database_engine(database_url)

    user_id = str(uuid4())
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, email, nickname, status, created_at, updated_at) "
                "VALUES (:id, :email, :nickname, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            ),
            {"id": user_id, "email": "constraint@example.com", "nickname": "constraint"},
        )

    with pytest.raises(IntegrityError):
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO user_profiles "
                    "(user_id, timezone, height_cm, personal_colors, updated_at) "
                    "VALUES (:user_id, 'UTC', 300, '{}', CURRENT_TIMESTAMP)"
                ),
                {"user_id": user_id},
            )

    engine.dispose()


def test_migrations_are_reversible_to_base(tmp_path) -> None:
    database_url = sqlite_url(tmp_path)
    upgrade_database(database_url)
    downgrade_database(database_url)

    engine = create_database_engine(database_url)
    assert set(inspect(engine).get_table_names()) <= {"alembic_version"}
    engine.dispose()


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="PostgreSQL test URL not configured")
def test_postgresql_migration_round_trip_matches_metadata() -> None:
    database_url = os.environ["TEST_POSTGRES_URL"]

    downgrade_database(database_url)
    upgrade_database(database_url)
    verify_database_schema(database_url)
    downgrade_database(database_url)
    upgrade_database(database_url)
    verify_database_schema(database_url)


@pytest.mark.skipif(not os.getenv("TEST_POSTGRES_URL"), reason="PostgreSQL test URL not configured")
def test_postgresql_legacy_create_all_upgrade_preserves_data() -> None:
    database_url = os.environ["TEST_POSTGRES_URL"]

    downgrade_database(database_url)
    engine = create_database_engine(database_url)
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE alembic_version"))
    engine.dispose()

    create_legacy_create_all_schema(database_url)
    user_id, closet_id, item_id = seed_legacy_data(database_url)
    engine = create_database_engine(database_url)
    assert inspect(engine).get_foreign_keys("items")[0]["name"] == "items_closet_id_fkey"
    engine.dispose()

    upgrade_database(database_url)
    verify_database_schema(database_url)
    assert_legacy_data_survived(database_url, user_id, closet_id, item_id)
