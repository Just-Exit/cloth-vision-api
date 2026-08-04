from uuid import UUID

from pydantic import BaseModel


class RecommendationResponse(BaseModel):
    source_item_id: UUID
    target_item_id: UUID
    overall_score: int
    scores: dict[str, int]
    reasons: list[str]
