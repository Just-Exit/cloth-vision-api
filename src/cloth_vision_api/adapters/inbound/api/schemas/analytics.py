from uuid import UUID

from cloth_vision_core import Category
from pydantic import BaseModel


class ColorDistributionResponse(BaseModel):
    color_name: str
    display_hex: str
    item_count: int
    ratio: float


class TagDistributionResponse(BaseModel):
    name: str
    item_count: int
    ratio: float


class CategoryDistributionResponse(BaseModel):
    category: Category
    item_count: int
    ratio: float


class EssentialRecommendationResponse(BaseModel):
    category: Category
    reason: str
    priority: int


class ClosetAnalyticsResponse(BaseModel):
    closet_id: UUID
    total_items: int
    color_distribution: list[ColorDistributionResponse]
    season_balance: list[TagDistributionResponse]
    category_distribution: list[CategoryDistributionResponse]
    essential_recommendations: list[EssentialRecommendationResponse]
