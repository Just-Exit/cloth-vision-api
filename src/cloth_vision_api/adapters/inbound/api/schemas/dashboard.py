from uuid import UUID

from cloth_vision_core import Category
from pydantic import BaseModel


class DashboardOutfitItemResponse(BaseModel):
    id: UUID
    category: Category
    display_name: str
    thumbnail_url: str


class DashboardOutfitResponse(BaseModel):
    id: UUID
    image_url: str
    reason: str
    items: list[DashboardOutfitItemResponse]


class ClosetSummaryResponse(BaseModel):
    completeness_score: int
    total_items: int
    covered_categories: list[Category]
    missing_categories: list[Category]


class RecentItemResponse(BaseModel):
    id: UUID
    display_name: str
    category: Category
    thumbnail_url: str
    created_at: str


class WeatherResponse(BaseModel):
    location: str
    temperature: float
    feels_like: float
    condition: str
    description: str
    precipitation: float
    humidity: int
    wind_speed: float
    observed_at: str
    fetched_at: str
    is_stale: bool


class DashboardResponse(BaseModel):
    nickname: str
    greeting: str
    today_outfit: DashboardOutfitResponse | None
    closet_summary: ClosetSummaryResponse
    stylist_tip: str
    weather: WeatherResponse | None
    recent_items: list[RecentItemResponse]
