from fastapi import APIRouter

from cloth_vision_api.adapters.inbound.api.routers import (
    auth,
    closets,
    health,
    items,
    recommendations,
)

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(auth.router)
router.include_router(closets.router)
router.include_router(items.router)
router.include_router(recommendations.router)
