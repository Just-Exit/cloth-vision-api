from typing import Annotated
from uuid import UUID

from cloth_vision_core import Category
from fastapi import APIRouter, File, Form, UploadFile, status

from cloth_vision_api.adapters.inbound.api.dependencies import (
    CurrentUser,
    ServiceDependency,
    SettingsDependency,
)
from cloth_vision_api.adapters.inbound.api.schemas import ItemResponse, ItemUpdate
from cloth_vision_api.application.errors import InvalidImageError

router = APIRouter(tags=["items"])


@router.post(
    "/closets/{closet_id}/items",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_item(
    closet_id: UUID,
    use_case: ServiceDependency,
    config: SettingsDependency,
    current_user: CurrentUser,
    display_name: Annotated[str, Form(min_length=1, max_length=120)],
    image: Annotated[UploadFile, File()],
    category: Annotated[Category | None, Form()] = None,
) -> ItemResponse:
    if image.content_type not in config.image_types:
        raise InvalidImageError("JPEG, PNG, WebP 이미지만 업로드할 수 있습니다.")
    if image.size is not None and image.size > config.max_upload_bytes:
        raise InvalidImageError(
            f"이미지는 {config.max_upload_bytes // (1024 * 1024)}MB 이하여야 합니다."
        )
    item = use_case.add_item(
        closet_id,
        current_user.id,
        display_name,
        image.filename or "upload",
        image.file,
        category,
    )
    return ItemResponse.model_validate(item)


@router.get("/closets/{closet_id}/items", response_model=list[ItemResponse])
def list_items(
    closet_id: UUID,
    use_case: ServiceDependency,
    current_user: CurrentUser,
) -> list[ItemResponse]:
    return [
        ItemResponse.model_validate(item)
        for item in use_case.list_items(closet_id, current_user.id)
    ]


@router.get("/items/{item_id}", response_model=ItemResponse)
def get_item(
    item_id: UUID,
    use_case: ServiceDependency,
    current_user: CurrentUser,
) -> ItemResponse:
    return ItemResponse.model_validate(use_case.get_item(item_id, current_user.id))


@router.patch("/items/{item_id}", response_model=ItemResponse)
def update_item(
    item_id: UUID,
    payload: ItemUpdate,
    use_case: ServiceDependency,
    current_user: CurrentUser,
) -> ItemResponse:
    item = use_case.update_item(
        item_id,
        current_user.id,
        payload.display_name,
        payload.category,
        payload.subcategory,
        payload.style_tags,
        payload.season_tags,
    )
    return ItemResponse.model_validate(item)


@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_item(
    item_id: UUID,
    use_case: ServiceDependency,
    current_user: CurrentUser,
) -> None:
    use_case.delete_item(item_id, current_user.id)
