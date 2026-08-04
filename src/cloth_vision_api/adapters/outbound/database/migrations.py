from __future__ import annotations

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

PROJECT_ROOT = Path(__file__).resolve().parents[5]

LEGACY_BASELINE_COLUMNS = {
    "users": {"id", "email", "nickname", "created_at"},
    "auth_identities": {
        "id",
        "user_id",
        "provider",
        "subject",
        "password_hash",
        "created_at",
    },
    "closets": {"id", "user_id", "name", "created_at"},
    "items": {
        "id",
        "closet_id",
        "display_name",
        "category",
        "subcategory",
        "status",
        "image_key",
        "color_hex",
        "color_name",
        "style_tags",
        "season_tags",
        "confidence",
        "user_attributes",
        "created_at",
        "updated_at",
    },
}


def alembic_config(database_url: str) -> Config:
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


def _stamp_matching_legacy_baseline(database_url: str, config: Config) -> None:
    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        table_names = set(inspector.get_table_names())
        if not table_names or "alembic_version" in table_names:
            return
        if table_names != set(LEGACY_BASELINE_COLUMNS):
            return

        actual_columns = {
            table_name: {column["name"] for column in inspector.get_columns(table_name)}
            for table_name in table_names
        }
        if actual_columns == LEGACY_BASELINE_COLUMNS:
            command.stamp(config, "0001")
    finally:
        engine.dispose()


def upgrade_database(database_url: str, revision: str = "head") -> None:
    config = alembic_config(database_url)
    _stamp_matching_legacy_baseline(database_url, config)
    command.upgrade(config, revision)


def downgrade_database(database_url: str, revision: str = "base") -> None:
    command.downgrade(alembic_config(database_url), revision)


def verify_database_schema(database_url: str) -> None:
    command.check(alembic_config(database_url))
