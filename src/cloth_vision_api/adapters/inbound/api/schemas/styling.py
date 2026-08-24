from uuid import UUID

from cloth_vision_core import Category
from pydantic import BaseModel, Field


class RecommendationResponse(BaseModel):
    source_item_id: UUID
    target_item_id: UUID
    overall_score: int
    scores: dict[str, int]
    reasons: list[str]


class OutfitRecommendationRequest(BaseModel):
    closet_id: UUID
    limit: int = Field(default=3, ge=1, le=10)


class OutfitItemResponse(BaseModel):
    id: UUID
    role: Category
    category: Category
    display_name: str
    thumbnail_url: str


class OutfitCandidateResponse(BaseModel):
    id: UUID
    image_url: str
    overall_score: int
    scores: dict[str, int]
    items: list[OutfitItemResponse]
    reasons: list[str]
    reason: str
    stylist_tip: str


class OutfitRecommendationsResponse(BaseModel):
    outfits: list[OutfitCandidateResponse]
    missing_categories: list[Category]
    evaluated_candidates: int
    message: str | None = None
