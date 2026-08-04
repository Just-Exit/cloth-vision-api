from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from cloth_vision_api.adapters.inbound.api.dependencies import (
    ClosetServiceDependency,
    CurrentUser,
)
from cloth_vision_api.adapters.inbound.api.schemas import RecommendationResponse

router = APIRouter(prefix="/items", tags=["recommendations"])


@router.get(
    "/{item_id}/recommendations",
    response_model=list[RecommendationResponse],
)
def recommendations(
    item_id: UUID,
    closet_service: ClosetServiceDependency,
    current_user: CurrentUser,
    limit: Annotated[int, Query(ge=1, le=20)] = 5,
) -> list[RecommendationResponse]:
    return [
        RecommendationResponse(
            source_item_id=item.source_item_id,
            target_item_id=item.target_item_id,
            overall_score=item.overall_score,
            scores={
                "color": item.color_score,
                "season": item.season_score,
                "style": item.style_score,
            },
            reasons=item.reasons,
        )
        for item in closet_service.recommendations(item_id, current_user.id, limit)
    ]
