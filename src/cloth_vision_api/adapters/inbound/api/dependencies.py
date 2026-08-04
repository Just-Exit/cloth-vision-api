from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer

from cloth_vision_api.application.identity import AuthService
from cloth_vision_api.application.wardrobe import ClosetService
from cloth_vision_api.config import Settings
from cloth_vision_api.domain.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def get_closet_service(request: Request) -> ClosetService:
    return request.app.state.closet_service


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_auth_service(request: Request) -> AuthService:
    return request.app.state.auth_service


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    return auth_service.user_from_token(token)


ClosetServiceDependency = Annotated[ClosetService, Depends(get_closet_service)]
SettingsDependency = Annotated[Settings, Depends(get_settings)]
AuthDependency = Annotated[AuthService, Depends(get_auth_service)]
CurrentUser = Annotated[User, Depends(get_current_user)]
