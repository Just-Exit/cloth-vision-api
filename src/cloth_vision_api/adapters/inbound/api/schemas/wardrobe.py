from datetime import datetime
from uuid import UUID

from cloth_vision_core import Category
from pydantic import BaseModel, ConfigDict, Field, computed_field

from cloth_vision_api.domain.models import ItemStatus


class ClosetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class ClosetResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemImageUrls(BaseModel):
    original_url: str
    transparent_url: str
    normalized_url: str
    thumbnail_url: str


class ItemResponse(BaseModel):
    id: UUID
    closet_id: UUID
    display_name: str
    category: Category
    subcategory: str | None
    status: ItemStatus
    color_hex: str | None
    color_name: str | None
    colors: list[dict]
    materials: list[dict]
    style_tags: list[str]
    season_tags: list[str]
    confidence: float | None
    user_attributes: dict[str, str]
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def image_url(self) -> str:
        return f"/api/v1/items/{self.id}/image"

    @computed_field
    @property
    def images(self) -> ItemImageUrls:
        base = f"/api/v1/items/{self.id}/images"
        return ItemImageUrls(
            original_url=f"{base}/original",
            transparent_url=f"{base}/transparent",
            normalized_url=f"{base}/normalized",
            thumbnail_url=f"{base}/thumbnail",
        )

    model_config = ConfigDict(from_attributes=True)


class ItemUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    category: Category | None = None
    subcategory: str | None = Field(default=None, max_length=60)
    style_tags: list[str] | None = None
    season_tags: list[str] | None = None
    colors: list[dict] | None = None
    materials: list[dict] | None = None
    user_attributes: dict[str, str] | None = None
