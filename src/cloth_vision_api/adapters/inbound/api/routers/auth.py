from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from cloth_vision_api.adapters.inbound.api.dependencies import (
    AuthDependency,
    CurrentUser,
)
from cloth_vision_api.adapters.inbound.api.schemas import (
    AuthResponse,
    LoginRequest,
    SignupRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _response(result: tuple) -> AuthResponse:
    user, token, expires_in = result
    return AuthResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user),
    )


@router.post(
    "/signup",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
)
def signup(payload: SignupRequest, auth_service: AuthDependency) -> AuthResponse:
    return _response(auth_service.signup(str(payload.email), payload.password, payload.nickname))


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, auth_service: AuthDependency) -> AuthResponse:
    return _response(auth_service.login(str(payload.email), payload.password))


@router.post("/token", response_model=AuthResponse, include_in_schema=False)
def oauth2_token(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthDependency,
) -> AuthResponse:
    return _response(auth_service.login(form.username, form.password))


@router.get("/me", response_model=UserResponse)
def me(current_user: CurrentUser) -> UserResponse:
    return UserResponse.model_validate(current_user)
