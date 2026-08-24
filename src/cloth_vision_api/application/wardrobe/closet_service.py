from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO
from uuid import NAMESPACE_URL, UUID, uuid5

from cloth_vision_core import (
    Category,
    ItemProfile,
    MatchingEngine,
    OutfitCandidate,
    OutfitExplanationProvider,
    OutfitImageComposer,
    OutfitRecommendationEngine,
    ProviderError,
)
from cloth_vision_core import (
    InvalidImageError as CoreInvalidImageError,
)

from cloth_vision_api.application.errors import InvalidImageError, NotFoundError
from cloth_vision_api.domain.models import Closet, FashionItem, ItemImageType, ItemStatus
from cloth_vision_api.ports.outbound import (
    IdentityRepository,
    ImageStorage,
    ItemAnalyzer,
    WardrobeRepository,
)


@dataclass(frozen=True, slots=True)
class GeneratedOutfit:
    id: UUID
    candidate: OutfitCandidate
    reason: str
    stylist_tip: str


@dataclass(frozen=True, slots=True)
class GeneratedOutfitRecommendations:
    outfits: list[GeneratedOutfit]
    missing_categories: list[Category]
    evaluated_candidates: int


class ClosetService:
    def __init__(
        self,
        identity_repository: IdentityRepository,
        wardrobe_repository: WardrobeRepository,
        storage: ImageStorage,
        analyzer: ItemAnalyzer,
        matching_engine: MatchingEngine,
        outfit_composer: OutfitImageComposer | None = None,
        outfit_explanation_provider: OutfitExplanationProvider | None = None,
    ) -> None:
        self.identity_repository = identity_repository
        self.wardrobe_repository = wardrobe_repository
        self.storage = storage
        self.analyzer = analyzer
        self.matching_engine = matching_engine
        self.outfit_engine = OutfitRecommendationEngine(matching_engine)
        self.outfit_composer = outfit_composer or OutfitImageComposer()
        self.outfit_explanation_provider = outfit_explanation_provider

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
            item.display_name = self._fallback_display_name(item.category)
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
            item.materials = []
            item.style_tags = result.style_tags
            item.season_tags = result.season_tags
            item.confidence = result.confidence
            item.user_attributes = result.attributes
            item.status = (
                ItemStatus.FAILED if result.attributes.get("analysis_warning") else ItemStatus.READY
            )
        except CoreInvalidImageError as exc:
            item.status = ItemStatus.FAILED
            self.wardrobe_repository.save_item(item)
            if item.image_key:
                self.storage.delete(item.image_key)
            raise InvalidImageError(str(exc)) from exc
        item.updated_at = datetime.now(UTC)
        return self.wardrobe_repository.save_item(item)

    @staticmethod
    def _fallback_display_name(category: Category) -> str:
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

    def get_item_image_path(
        self,
        item_id: UUID,
        user_id: UUID,
        image_type: ItemImageType = ItemImageType.ORIGINAL,
    ) -> Path:
        item = self.get_item(item_id, user_id)
        if not item.image_key:
            raise NotFoundError("아이템 이미지를 찾을 수 없습니다.")
        original = self.storage.path_for(item.image_key)
        if not original.is_file():
            raise NotFoundError("아이템 이미지를 찾을 수 없습니다.")
        if image_type is ItemImageType.ORIGINAL:
            return original
        derived_names = {
            ItemImageType.TRANSPARENT: "transparent.png",
            ItemImageType.NORMALIZED: "normalized.jpg",
            ItemImageType.THUMBNAIL: "thumbnail.webp",
        }
        derived = original.parent / "derived" / derived_names[image_type]
        # Older items and segmentation-disabled uploads remain displayable.
        return derived if derived.is_file() else original

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

    def outfit_recommendations(
        self, closet_id: UUID, user_id: UUID, limit: int
    ) -> tuple[GeneratedOutfitRecommendations, dict[UUID, FashionItem]]:
        self._owned_closet(closet_id, user_id)
        items = [
            item
            for item in self.wardrobe_repository.list_items(closet_id)
            if item.status == ItemStatus.READY
        ]
        items_by_id = {item.id: item for item in items}
        result = self.outfit_engine.recommend([self._profile(item) for item in items], limit=limit)
        generated = []
        for candidate in result.outfits:
            outfit_id = uuid5(
                NAMESPACE_URL,
                f"cloth-vision:{user_id}:"
                + ",".join(str(item_id) for item_id in candidate.item_ids),
            )
            candidate_items = [items_by_id[item_id] for item_id in candidate.item_ids]
            sources = [
                (item.category, self._best_composite_source(item)) for item in candidate_items
            ]
            self.outfit_composer.compose(sources, self.storage.outfit_path(user_id, outfit_id))
            reason, tip = self._outfit_copy(candidate, candidate_items)
            generated.append(GeneratedOutfit(outfit_id, candidate, reason, tip))
        return (
            GeneratedOutfitRecommendations(
                generated, result.missing_categories, result.evaluated_candidates
            ),
            items_by_id,
        )

    def get_outfit_image_path(self, outfit_id: UUID, user_id: UUID) -> Path:
        path = self.storage.outfit_path(user_id, outfit_id)
        if not path.is_file():
            raise NotFoundError("추천 코디 이미지를 찾을 수 없습니다.")
        return path

    def _best_composite_source(self, item: FashionItem) -> Path:
        if not item.image_key:
            raise NotFoundError("아이템 이미지를 찾을 수 없습니다.")
        original = self.storage.path_for(item.image_key)
        for name in ("transparent.png", "normalized.jpg"):
            derived = original.parent / "derived" / name
            if derived.is_file():
                return derived
        if not original.is_file():
            raise NotFoundError("아이템 이미지를 찾을 수 없습니다.")
        return original

    def _outfit_copy(self, candidate: OutfitCandidate, items: list[FashionItem]) -> tuple[str, str]:
        if self.outfit_explanation_provider:
            try:
                explanation = self.outfit_explanation_provider.explain(
                    candidate, [self._profile(item) for item in items]
                )
                return explanation.reason, explanation.stylist_tip
            except ProviderError:
                pass
        if candidate.color_score >= max(candidate.season_score, candidate.style_score):
            return "색상 조화가 안정적인 코디입니다.", "같은 톤의 소품으로 정리해보세요."
        if candidate.season_score >= candidate.style_score:
            return "계절감이 자연스럽게 이어지는 코디입니다.", "가벼운 레이어링으로 완성해보세요."
        return "스타일 분위기가 잘 어울리는 코디입니다.", "포인트 아이템은 하나만 더해보세요."

    @staticmethod
    def _profile(item: FashionItem) -> ItemProfile:
        return ItemProfile(
            id=item.id,
            category=item.category,
            color_hex=item.color_hex,
            style_tags=item.style_tags,
            season_tags=item.season_tags,
        )
