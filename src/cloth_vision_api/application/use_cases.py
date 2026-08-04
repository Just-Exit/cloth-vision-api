from __future__ import annotations

from datetime import UTC, datetime
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
from cloth_vision_api.ports.outbound import ImageStorage, ItemAnalyzer, Repository


class ClosetService:
    def __init__(
        self,
        repository: Repository,
        storage: ImageStorage,
        analyzer: ItemAnalyzer,
        matching_engine: MatchingEngine,
    ) -> None:
        self.repository = repository
        self.storage = storage
        self.analyzer = analyzer
        self.matching_engine = matching_engine

    def create_closet(self, user_id: UUID, name: str) -> Closet:
        if not self.repository.get_user(user_id):
            raise NotFoundError("사용자를 찾을 수 없습니다.")
        return self.repository.add_closet(Closet(user_id=user_id, name=name))

    def list_closets(self, user_id: UUID) -> list[Closet]:
        if not self.repository.get_user(user_id):
            raise NotFoundError("사용자를 찾을 수 없습니다.")
        return self.repository.list_closets(user_id)

    def _owned_closet(self, closet_id: UUID, user_id: UUID) -> Closet:
        closet = self.repository.get_closet(closet_id)
        if not closet or closet.user_id != user_id:
            raise NotFoundError("옷장을 찾을 수 없습니다.")
        return closet

    def add_item(
        self,
        closet_id: UUID,
        user_id: UUID,
        display_name: str,
        filename: str,
        stream: BinaryIO,
        category_hint: Category | None = None,
    ) -> FashionItem:
        self._owned_closet(closet_id, user_id)
        item = self.repository.add_item(FashionItem(closet_id=closet_id, display_name=display_name))
        try:
            item.image_key = self.storage.save(item.id, filename, stream)
            result = self.analyzer.analyze(self.storage.path_for(item.image_key))
            item.category = category_hint or result.category
            item.subcategory = result.subcategory
            item.color_hex = result.color_hex
            item.color_name = result.color_name
            item.style_tags = result.style_tags
            item.season_tags = result.season_tags
            item.confidence = result.confidence
            item.user_attributes = result.attributes
            item.status = ItemStatus.READY
        except CoreInvalidImageError as exc:
            item.status = ItemStatus.FAILED
            self.repository.save_item(item)
            if item.image_key:
                self.storage.delete(item.image_key)
            raise InvalidImageError(str(exc)) from exc
        item.updated_at = datetime.now(UTC)
        return self.repository.save_item(item)

    def get_item(self, item_id: UUID, user_id: UUID) -> FashionItem:
        item = self.repository.get_item(item_id)
        if not item:
            raise NotFoundError("아이템을 찾을 수 없습니다.")
        self._owned_closet(item.closet_id, user_id)
        return item

    def list_items(self, closet_id: UUID, user_id: UUID) -> list[FashionItem]:
        self._owned_closet(closet_id, user_id)
        return self.repository.list_items(closet_id)

    def update_item(
        self,
        item_id: UUID,
        user_id: UUID,
        display_name: str | None,
        category: Category | None,
        subcategory: str | None,
        style_tags: list[str] | None,
        season_tags: list[str] | None,
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
        item.updated_at = datetime.now(UTC)
        return self.repository.save_item(item)

    def delete_item(self, item_id: UUID, user_id: UUID) -> None:
        item = self.get_item(item_id, user_id)
        if not self.repository.delete_item(item_id):
            raise NotFoundError("아이템을 찾을 수 없습니다.")
        if item.image_key:
            self.storage.delete(item.image_key)

    def recommendations(self, item_id: UUID, user_id: UUID, limit: int) -> list:
        source = self.get_item(item_id, user_id)
        candidates = [
            item
            for item in self.repository.list_items(source.closet_id)
            if item.id != source.id and item.status == ItemStatus.READY
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
