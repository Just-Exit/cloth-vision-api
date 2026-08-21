from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO
from uuid import UUID

from cloth_vision_core import (
    Category,
    ItemProfile,
    MatchingEngine,
)
from cloth_vision_core import (
    InvalidImageError as CoreInvalidImageError,
)

from cloth_vision_api.application.errors import InvalidImageError, NotFoundError
from cloth_vision_api.domain.models import Closet, FashionItem, ItemStatus
from cloth_vision_api.ports.outbound import (
    IdentityRepository,
    ImageStorage,
    ItemAnalyzer,
    WardrobeRepository,
)


class ClosetService:
    def __init__(
        self,
        identity_repository: IdentityRepository,
        wardrobe_repository: WardrobeRepository,
        storage: ImageStorage,
        analyzer: ItemAnalyzer,
        matching_engine: MatchingEngine,
    ) -> None:
        self.identity_repository = identity_repository
        self.wardrobe_repository = wardrobe_repository
        self.storage = storage
        self.analyzer = analyzer
        self.matching_engine = matching_engine

    def create_closet(self, user_id: UUID, name: str) -> Closet:
        if not self.identity_repository.get_user(user_id):
            raise NotFoundError("사용자를 찾을 수 없습니다.")
        return self.wardrobe_repository.add_closet(Closet(user_id=user_id, name=name))

    def list_closets(self, user_id: UUID) -> list[Closet]:
        if not self.identity_repository.get_user(user_id):
            raise NotFoundError("사용자를 찾을 수 없습니다.")
        return self.wardrobe_repository.list_closets(user_id)

    def _owned_closet(self, closet_id: UUID, user_id: UUID) -> Closet:
        closet = self.wardrobe_repository.get_closet(closet_id)
        if not closet or closet.user_id != user_id:
            raise NotFoundError("옷장을 찾을 수 없습니다.")
        return closet

    def add_item(
        self,
        closet_id: UUID,
        user_id: UUID,
        filename: str,
        stream: BinaryIO,
        category_hint: Category | None = None,
    ) -> FashionItem:
        self._owned_closet(closet_id, user_id)
        item = self.wardrobe_repository.add_item(
            FashionItem(closet_id=closet_id, display_name="분석 중인 의류")
        )
        try:
            item.image_key = self.storage.save(item.id, filename, stream)
            result = self.analyzer.analyze(self.storage.path_for(item.image_key))
            item.category = category_hint or result.category
            item.subcategory = result.subcategory
            item.display_name = result.suggested_display_name or self._fallback_display_name(
                item.category, item.subcategory
            )
            item.color_hex = result.color_hex
            item.color_name = result.color_name
            item.colors = [
                {
                    "display_hex": color.display_hex,
                    "color_name": color.color_name,
                    "ratio": color.ratio,
                    "confidence": color.confidence,
                }
                for color in result.colors
            ]
            item.materials = [
                {
                    "name": material.name,
                    "confidence": material.confidence,
                    "source": material.source,
                }
                for material in result.materials
            ]
            item.style_tags = result.style_tags
            item.season_tags = result.season_tags
            item.confidence = result.confidence
            item.user_attributes = result.attributes
            item.status = ItemStatus.READY
        except CoreInvalidImageError as exc:
            item.status = ItemStatus.FAILED
            self.wardrobe_repository.save_item(item)
            if item.image_key:
                self.storage.delete(item.image_key)
            raise InvalidImageError(str(exc)) from exc
        item.updated_at = datetime.now(UTC)
        return self.wardrobe_repository.save_item(item)

    @staticmethod
    def _fallback_display_name(category: Category, subcategory: str | None) -> str:
        if subcategory and subcategory != "unclassified":
            return subcategory.replace("_", " ")[:120]
        names = {
            Category.TOP: "상의",
            Category.BOTTOM: "하의",
            Category.OUTER: "아우터",
            Category.SHOES: "신발",
            Category.ACCESSORY: "액세서리",
            Category.UNKNOWN: "의류",
        }
        return names[category]

    def get_item(self, item_id: UUID, user_id: UUID) -> FashionItem:
        item = self.wardrobe_repository.get_item(item_id)
        if not item:
            raise NotFoundError("아이템을 찾을 수 없습니다.")
        self._owned_closet(item.closet_id, user_id)
        return item

    def get_item_image_path(self, item_id: UUID, user_id: UUID) -> Path:
        item = self.get_item(item_id, user_id)
        if not item.image_key:
            raise NotFoundError("아이템 이미지를 찾을 수 없습니다.")
        path = self.storage.path_for(item.image_key)
        if not path.is_file():
            raise NotFoundError("아이템 이미지를 찾을 수 없습니다.")
        return path

    def list_items(self, closet_id: UUID, user_id: UUID) -> list[FashionItem]:
        self._owned_closet(closet_id, user_id)
        return self.wardrobe_repository.list_items(closet_id)

    def update_item(
        self,
        item_id: UUID,
        user_id: UUID,
        display_name: str | None,
        category: Category | None,
        subcategory: str | None,
        style_tags: list[str] | None,
        season_tags: list[str] | None,
        colors: list[dict] | None,
        materials: list[dict] | None,
        user_attributes: dict[str, str] | None,
    ) -> FashionItem:
        item = self.get_item(item_id, user_id)
        if display_name is not None:
            item.display_name = display_name
        if category is not None:
            item.category = category
        if subcategory is not None:
            item.subcategory = subcategory
        if style_tags is not None:
            item.style_tags = style_tags
        if season_tags is not None:
            item.season_tags = season_tags
        if colors is not None:
            item.colors = colors
            if colors:
                item.color_hex = colors[0].get("display_hex", item.color_hex)
                item.color_name = colors[0].get("color_name", item.color_name)
        if materials is not None:
            item.materials = materials
        if user_attributes is not None:
            item.user_attributes = user_attributes
        item.updated_at = datetime.now(UTC)
        return self.wardrobe_repository.save_item(item)

    def delete_item(self, item_id: UUID, user_id: UUID) -> None:
        item = self.get_item(item_id, user_id)
        if not self.wardrobe_repository.delete_item(item_id):
            raise NotFoundError("아이템을 찾을 수 없습니다.")
        if item.image_key:
            self.storage.delete(item.image_key)

    def recommendations(self, item_id: UUID, user_id: UUID, limit: int) -> list:
        source = self.get_item(item_id, user_id)
        candidates = [
            item
            for item in self.wardrobe_repository.list_items(source.closet_id)
            if item.id != source.id
            and item.status == ItemStatus.READY
            and item.category != source.category
        ]
        source_profile = self._profile(source)
        scored = [
            self.matching_engine.compare(source_profile, self._profile(target))
            for target in candidates
        ]
        return sorted(scored, key=lambda item: item.overall_score, reverse=True)[:limit]

    @staticmethod
    def _profile(item: FashionItem) -> ItemProfile:
        return ItemProfile(
            id=item.id,
            category=item.category,
            color_hex=item.color_hex,
            style_tags=item.style_tags,
            season_tags=item.season_tags,
        )
