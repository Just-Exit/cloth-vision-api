from uuid import UUID

from fastapi import APIRouter

from cloth_vision_api.adapters.inbound.api.dependencies import (
    ClosetServiceDependency,
    CurrentUser,
)
from cloth_vision_api.adapters.inbound.api.schemas.dashboard import DashboardResponse

router = APIRouter(tags=["dashboard"])


@router.get("/closets/{closet_id}/dashboard", response_model=DashboardResponse)
def dashboard(
    closet_id: UUID,
    closet_service: ClosetServiceDependency,
    current_user: CurrentUser,
) -> DashboardResponse:
    return DashboardResponse.model_validate(closet_service.dashboard(closet_id, current_user.id))
