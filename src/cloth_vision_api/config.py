from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Cloth Vision API"
    app_env: str = "local"
    database_url: str = "postgresql+psycopg://cloth_vision:cloth_vision@localhost:5432/cloth_vision"
    upload_dir: Path = Path("./var/uploads")
    max_upload_bytes: int = 10 * 1024 * 1024
    allowed_image_types: str = "image/jpeg,image/png,image/webp"
    jwt_secret_key: str = "local-development-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def image_types(self) -> set[str]:
        return {value.strip() for value in self.allowed_image_types.split(",")}
