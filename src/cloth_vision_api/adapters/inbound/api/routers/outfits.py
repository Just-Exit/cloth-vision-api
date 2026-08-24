from uuid import UUID

from fastapi import APIRouter
from fastapi.responses import FileResponse

from cloth_vision_api.adapters.inbound.api.dependencies import (
    ClosetServiceDependency,
    CurrentUser,
)
from cloth_vision_api.adapters.inbound.api.schemas.styling import (
    OutfitCandidateResponse,
    OutfitItemResponse,
    OutfitRecommendationRequest,
    OutfitRecommendationsResponse,
)

router = APIRouter(tags=["outfit-recommendations"])


@router.post("/outfit-recommendations", response_model=OutfitRecommendationsResponse)
def recommend_outfits(
    payload: OutfitRecommendationRequest,
    closet_service: ClosetServiceDependency,
    current_user: CurrentUser,
) -> OutfitRecommendationsResponse:
    result, items_by_id = closet_service.outfit_recommendations(
        payload.closet_id, current_user.id, payload.limit
    )
    outfits = []
    for generated in result.outfits:
        candidate = generated.candidate
        outfit_items = []
        for item_id in candidate.item_ids:
            item = items_by_id[item_id]
            outfit_items.append(
                OutfitItemResponse(
                    id=item.id,
                    role=item.category,
                    category=item.category,
                    display_name=item.display_name,
                    thumbnail_url=f"/api/v1/items/{item.id}/images/thumbnail",
                )
            )
        outfits.append(
            OutfitCandidateResponse(
                id=generated.id,
                image_url=f"/api/v1/outfit-recommendations/{generated.id}/image",
                overall_score=candidate.overall_score,
                scores={
                    "color": candidate.color_score,
                    "season": candidate.season_score,
                    "style": candidate.style_score,
                },
                items=outfit_items,
                reasons=candidate.reasons,
                reason=generated.reason,
                stylist_tip=generated.stylist_tip,
            )
        )
    missing = result.missing_categories
    message = (
        f"코디 추천을 위해 {', '.join(category.value for category in missing)} 아이템을 "
        "등록해주세요."
        if missing
        else None
    )
    return OutfitRecommendationsResponse(
        outfits=outfits,
        missing_categories=missing,
        evaluated_candidates=result.evaluated_candidates,
        message=message,
    )


@router.get("/outfit-recommendations/{outfit_id}/image", response_class=FileResponse)
def get_outfit_image(
    outfit_id: UUID,
    closet_service: ClosetServiceDependency,
    current_user: CurrentUser,
) -> FileResponse:
    path = closet_service.get_outfit_image_path(outfit_id, current_user.id)
    return FileResponse(path, media_type="image/webp", filename=f"{outfit_id}.webp")
