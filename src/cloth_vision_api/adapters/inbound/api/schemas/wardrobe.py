from datetime import datetime
from uuid import UUID

from cloth_vision_core import Category
from pydantic import BaseModel, ConfigDict, Field

from cloth_vision_api.domain.models import ItemStatus


class ClosetCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)


class ClosetResponse(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemResponse(BaseModel):
    id: UUID
    closet_id: UUID
    display_name: str
    category: Category
    subcategory: str | None
    status: ItemStatus
    color_hex: str | None
    color_name: str | None
    style_tags: list[str]
    season_tags: list[str]
    confidence: float | None
    user_attributes: dict[str, str]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ItemUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    category: Category | None = None
    subcategory: str | None = Field(default=None, max_length=60)
    style_tags: list[str] | None = None
    season_tags: list[str] | None = None
