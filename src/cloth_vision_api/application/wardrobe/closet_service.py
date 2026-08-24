from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO
from uuid import NAMESPACE_URL, UUID, uuid5
from zoneinfo import ZoneInfo

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
    WeatherCache,
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
        weather_cache: WeatherCache | None = None,
    ) -> None:
        self.identity_repository = identity_repository
        self.wardrobe_repository = wardrobe_repository
        self.storage = storage
        self.analyzer = analyzer
        self.matching_engine = matching_engine
        self.outfit_engine = OutfitRecommendationEngine(matching_engine)
        self.outfit_composer = outfit_composer or OutfitImageComposer()
        self.outfit_explanation_provider = outfit_explanation_provider
        self.weather_cache = weather_cache

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

    def closet_analytics(self, closet_id: UUID, user_id: UUID) -> dict:
        self._owned_closet(closet_id, user_id)
        items = [
            item
            for item in self.wardrobe_repository.list_items(closet_id)
            if item.status == ItemStatus.READY
        ]
        total = len(items)

        color_counts: Counter[tuple[str, str]] = Counter()
        for item in items:
            primary = item.colors[0] if item.colors else None
            display_hex = (primary or {}).get("display_hex") or item.color_hex
            color_name = (primary or {}).get("color_name") or item.color_name
            if display_hex and color_name:
                color_counts[(str(color_name), str(display_hex).upper())] += 1

        season_counts = Counter(
            season for item in items for season in set(item.season_tags) if season
        )
        category_counts = Counter(
            item.category for item in items if item.category is not Category.UNKNOWN
        )
        required = (
            Category.TOP,
            Category.BOTTOM,
            Category.OUTER,
            Category.SHOES,
            Category.ACCESSORY,
        )
        labels = {
            Category.TOP: "상의가 없어 기본 코디를 구성하기 어렵습니다.",
            Category.BOTTOM: "하의가 없어 기본 코디를 구성하기 어렵습니다.",
            Category.OUTER: "아우터를 추가하면 레이어드 코디의 폭이 넓어집니다.",
            Category.SHOES: "신발을 추가하면 완성된 코디를 추천할 수 있습니다.",
            Category.ACCESSORY: "액세서리를 추가하면 포인트 코디가 다양해집니다.",
        }

        return {
            "closet_id": closet_id,
            "total_items": total,
            "color_distribution": [
                {
                    "color_name": name,
                    "display_hex": display_hex,
                    "item_count": count,
                    "ratio": self._ratio(count, sum(color_counts.values())),
                }
                for (name, display_hex), count in color_counts.most_common()
            ],
            "season_balance": [
                {
                    "name": name,
                    "item_count": count,
                    "ratio": self._ratio(count, sum(season_counts.values())),
                }
                for name, count in season_counts.most_common()
            ],
            "category_distribution": [
                {
                    "category": category,
                    "item_count": count,
                    "ratio": self._ratio(count, sum(category_counts.values())),
                }
                for category, count in category_counts.most_common()
            ],
            "essential_recommendations": [
                {"category": category, "reason": labels[category], "priority": priority}
                for priority, category in enumerate(
                    (category for category in required if category_counts[category] == 0),
                    start=1,
                )
            ][:3],
        }

    def dashboard(self, closet_id: UUID, user_id: UUID) -> dict:
        user = self.identity_repository.get_user(user_id)
        if not user:
            raise NotFoundError("사용자를 찾을 수 없습니다.")
        self._owned_closet(closet_id, user_id)
        items = [
            item
            for item in self.wardrobe_repository.list_items(closet_id)
            if item.status == ItemStatus.READY
        ]
        target_categories = (
            Category.TOP,
            Category.BOTTOM,
            Category.OUTER,
            Category.SHOES,
            Category.ACCESSORY,
        )
        present = {item.category for item in items}
        covered = [category for category in target_categories if category in present]
        missing = [category for category in target_categories if category not in present]

        weather = self.weather_cache.get() if self.weather_cache else None
        preferred_seasons = self._weather_seasons(weather.temperature) if weather else None
        recommendations, items_by_id = self.outfit_recommendations(
            closet_id, user_id, 1, preferred_seasons=preferred_seasons
        )
        generated = recommendations.outfits[0] if recommendations.outfits else None
        today_outfit = None
        if generated:
            today_outfit = {
                "id": generated.id,
                "image_url": (
                    f"/api/v1/closets/{closet_id}/outfit-recommendations/{generated.id}/image"
                ),
                "reason": (
                    f"서울 {weather.temperature:.0f}°C 날씨와 계절 태그를 고려한 코디입니다."
                    if weather
                    else generated.reason
                ),
                "items": [
                    {
                        "id": item_id,
                        "category": items_by_id[item_id].category,
                        "display_name": items_by_id[item_id].display_name,
                        "thumbnail_url": f"/api/v1/items/{item_id}/images/thumbnail",
                    }
                    for item_id in generated.candidate.item_ids
                ],
            }

        hour = datetime.now(ZoneInfo("Asia/Seoul")).hour
        greeting = (
            "좋은 아침입니다"
            if hour < 12
            else "좋은 오후입니다"
            if hour < 18
            else "좋은 저녁입니다"
        )
        stylist_tip = (
            generated.stylist_tip
            if generated
            else "상의와 하의를 등록하면 오늘의 코디를 추천해드릴게요."
        )
        return {
            "nickname": user.nickname,
            "greeting": greeting,
            "today_outfit": today_outfit,
            "closet_summary": {
                "completeness_score": round(len(covered) / len(target_categories) * 100),
                "total_items": len(items),
                "covered_categories": covered,
                "missing_categories": missing,
            },
            "stylist_tip": stylist_tip,
            "weather": self._weather_payload(weather),
            "recent_items": [
                {
                    "id": item.id,
                    "display_name": item.display_name,
                    "category": item.category,
                    "thumbnail_url": f"/api/v1/items/{item.id}/images/thumbnail",
                    "created_at": item.created_at.isoformat(),
                }
                for item in items[:5]
            ],
        }

    @staticmethod
    def _weather_seasons(temperature: float) -> set[str]:
        if temperature < 10:
            return {"winter"}
        if temperature < 20:
            return {"spring", "fall"}
        if temperature < 28:
            return {"spring", "summer", "fall"}
        return {"summer"}

    @staticmethod
    def _weather_payload(weather) -> dict | None:
        if weather is None:
            return None
        return {
            "location": weather.location,
            "temperature": weather.temperature,
            "feels_like": weather.feels_like,
            "condition": weather.condition,
            "description": weather.description,
            "precipitation": weather.precipitation,
            "humidity": weather.humidity,
            "wind_speed": weather.wind_speed,
            "observed_at": weather.observed_at.isoformat(),
            "fetched_at": weather.fetched_at.isoformat(),
            "is_stale": weather.is_stale,
        }

    @staticmethod
    def _ratio(count: int, total: int) -> float:
        return round(count / total, 4) if total else 0.0

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
        self,
        closet_id: UUID,
        user_id: UUID,
        limit: int,
        *,
        preferred_seasons: set[str] | None = None,
    ) -> tuple[GeneratedOutfitRecommendations, dict[UUID, FashionItem]]:
        self._owned_closet(closet_id, user_id)
        items = [
            item
            for item in self.wardrobe_repository.list_items(closet_id)
            if item.status == ItemStatus.READY
        ]
        items_by_id = {item.id: item for item in items}
        result = self.outfit_engine.recommend(
            [self._profile(item) for item in items],
            limit=max(limit * 3, limit) if preferred_seasons else limit,
        )
        candidates = result.outfits
        if preferred_seasons:
            candidates = sorted(
                candidates,
                key=lambda candidate: (
                    self._candidate_weather_score(candidate, items_by_id, preferred_seasons),
                    candidate.overall_score,
                ),
                reverse=True,
            )[:limit]
        generated = []
        for candidate in candidates:
            outfit_id = uuid5(
                NAMESPACE_URL,
                f"cloth-vision:{user_id}:"
                + ",".join(str(item_id) for item_id in candidate.item_ids),
            )
            candidate_items = [items_by_id[item_id] for item_id in candidate.item_ids]
            sources = [
                (item.category, self._best_composite_source(item)) for item in candidate_items
            ]
            self.outfit_composer.compose(
                sources, self.storage.outfit_path(user_id, closet_id, outfit_id)
            )
            reason, tip = self._outfit_copy(candidate, candidate_items)
            generated.append(GeneratedOutfit(outfit_id, candidate, reason, tip))
        return (
            GeneratedOutfitRecommendations(
                generated, result.missing_categories, result.evaluated_candidates
            ),
            items_by_id,
        )

    @staticmethod
    def _candidate_weather_score(
        candidate: OutfitCandidate,
        items_by_id: dict[UUID, FashionItem],
        preferred_seasons: set[str],
    ) -> float:
        tags = [
            set(items_by_id[item_id].season_tags)
            for item_id in candidate.item_ids
            if items_by_id[item_id].season_tags
        ]
        return (
            sum(bool(item_tags & preferred_seasons) for item_tags in tags) / len(tags)
            if tags
            else 0.0
        )

    def get_outfit_image_path(self, closet_id: UUID, outfit_id: UUID, user_id: UUID) -> Path:
        self._owned_closet(closet_id, user_id)
        path = self.storage.outfit_path(user_id, closet_id, outfit_id)
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
