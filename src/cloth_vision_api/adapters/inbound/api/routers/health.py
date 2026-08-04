from fastapi import APIRouter

from cloth_vision_api.adapters.inbound.api.dependencies import SettingsDependency
from cloth_vision_api.adapters.inbound.api.schemas import HealthResponse

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health(config: SettingsDependency) -> HealthResponse:
    return HealthResponse(status="ok", environment=config.app_env)
