from uuid import UUID

from fastapi import APIRouter

from cloth_vision_api.adapters.inbound.api.dependencies import (
    ClosetServiceDependency,
    CurrentUser,
)
from cloth_vision_api.adapters.inbound.api.schemas.analytics import ClosetAnalyticsResponse

router = APIRouter(tags=["closet-analytics"])


@router.get("/closets/{closet_id}/analytics", response_model=ClosetAnalyticsResponse)
def closet_analytics(
    closet_id: UUID,
    closet_service: ClosetServiceDependency,
    current_user: CurrentUser,
) -> ClosetAnalyticsResponse:
    return ClosetAnalyticsResponse.model_validate(
        closet_service.closet_analytics(closet_id, current_user.id)
    )
