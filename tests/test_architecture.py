from pathlib import Path

from cloth_vision_api.adapters.outbound.database import (
    SqlAlchemyIdentityRepository,
    SqlAlchemyWardrobeRepository,
)
from cloth_vision_api.config import Settings
from cloth_vision_api.main import create_app

PACKAGE_ROOT = Path(__file__).parents[1] / "src" / "cloth_vision_api"


def test_composition_root_shares_session_factory_across_repositories(tmp_path) -> None:
    app = create_app(
        Settings(
            app_env="test",
            database_url=f"sqlite:///{tmp_path / 'architecture.db'}",
            upload_dir=tmp_path / "uploads",
            run_database_migrations=False,
        )
    )

    identity_repository = app.state.auth_service.identity_repository
    closet_service = app.state.closet_service

    assert isinstance(identity_repository, SqlAlchemyIdentityRepository)
    assert closet_service.identity_repository is identity_repository
    assert isinstance(closet_service.wardrobe_repository, SqlAlchemyWardrobeRepository)
    assert closet_service.wardrobe_repository.session_factory is identity_repository.session_factory


def test_domain_and_application_do_not_import_framework_adapters() -> None:
    forbidden_imports = ("fastapi", "sqlalchemy", "cloth_vision_api.adapters")

    for layer_name in ("domain", "application", "ports"):
        for source_path in (PACKAGE_ROOT / layer_name).rglob("*.py"):
            source = source_path.read_text()
            assert not any(name in source for name in forbidden_imports), source_path
