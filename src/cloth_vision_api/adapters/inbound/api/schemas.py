from __future__ import annotations

from datetime import datetime
from uuid import UUID

from cloth_vision_core import Category
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from cloth_vision_api.domain.models import ItemStatus


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    nickname: str = Field(min_length=1, max_length=80)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: UUID
    email: str
    nickname: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


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


class RecommendationResponse(BaseModel):
    source_item_id: UUID
    target_item_id: UUID
    overall_score: int
    scores: dict[str, int]
    reasons: list[str]


class HealthResponse(BaseModel):
    status: str
    environment: str
