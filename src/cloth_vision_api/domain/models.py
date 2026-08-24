from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from cloth_vision_core import Category


def utc_now() -> datetime:
    return datetime.now(UTC)


class ItemStatus(StrEnum):
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ItemImageType(StrEnum):
    ORIGINAL = "original"
    TRANSPARENT = "transparent"
    NORMALIZED = "normalized"
    THUMBNAIL = "thumbnail"


class AuthProvider(StrEnum):
    LOCAL = "local"
    GOOGLE = "google"
    APPLE = "apple"


@dataclass(frozen=True, slots=True)
class User:
    email: str
    nickname: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class AuthIdentity:
    user_id: UUID
    provider: AuthProvider
    subject: str
    password_hash: str | None = None
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class Closet:
    user_id: UUID
    name: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(slots=True)
class FashionItem:
    closet_id: UUID
    display_name: str
    category: Category = Category.UNKNOWN
    subcategory: str | None = None
    status: ItemStatus = ItemStatus.PROCESSING
    image_key: str | None = None
    color_hex: str | None = None
    color_name: str | None = None
    colors: list[dict] = field(default_factory=list)
    materials: list[dict] = field(default_factory=list)
    style_tags: list[str] = field(default_factory=list)
    season_tags: list[str] = field(default_factory=list)
    confidence: float | None = None
    user_attributes: dict[str, str] = field(default_factory=dict)
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
