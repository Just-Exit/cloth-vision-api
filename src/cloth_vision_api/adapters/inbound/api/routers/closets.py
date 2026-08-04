from fastapi import APIRouter, status

from cloth_vision_api.adapters.inbound.api.dependencies import CurrentUser, ServiceDependency
from cloth_vision_api.adapters.inbound.api.schemas import ClosetCreate, ClosetResponse

router = APIRouter(tags=["closets"])


@router.post(
    "/closets",
    response_model=ClosetResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_closet(
    payload: ClosetCreate,
    use_case: ServiceDependency,
    current_user: CurrentUser,
) -> ClosetResponse:
    return ClosetResponse.model_validate(use_case.create_closet(current_user.id, payload.name))


@router.get("/closets", response_model=list[ClosetResponse])
def list_closets(use_case: ServiceDependency, current_user: CurrentUser) -> list[ClosetResponse]:
    return [ClosetResponse.model_validate(item) for item in use_case.list_closets(current_user.id)]
