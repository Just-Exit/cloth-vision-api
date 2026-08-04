from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from cloth_vision_core import AnalysisPipeline, MatchingEngine, PillowImageProcessor
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cloth_vision_api.adapters.inbound.api.router import router
from cloth_vision_api.adapters.outbound.database import SqlAlchemyRepository
from cloth_vision_api.adapters.outbound.security import Argon2PasswordManager, JwtTokenManager
from cloth_vision_api.adapters.outbound.storage import LocalImageStorage
from cloth_vision_api.application.auth import AuthService
from cloth_vision_api.application.errors import (
    ApplicationError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from cloth_vision_api.application.use_cases import ClosetService
from cloth_vision_api.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    Path("./var").mkdir(parents=True, exist_ok=True)
    repository = SqlAlchemyRepository(config.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        repository.create_schema()
        yield

    app = FastAPI(
        title=config.app_name,
        version="0.1.0",
        description="AI Fashion Coach MVP backend",
        lifespan=lifespan,
    )
    app.state.settings = config
    app.state.service = ClosetService(
        repository,
        LocalImageStorage(config.upload_dir),
        AnalysisPipeline(PillowImageProcessor()),
        MatchingEngine(),
    )
    app.state.auth_service = AuthService(
        repository,
        Argon2PasswordManager(),
        JwtTokenManager(
            config.jwt_secret_key,
            config.jwt_algorithm,
            config.access_token_expire_minutes,
        ),
    )
    app.include_router(router)

    @app.exception_handler(ApplicationError)
    async def application_error(_: Request, exc: ApplicationError) -> JSONResponse:
        status_code = (
            404
            if isinstance(exc, NotFoundError)
            else 401
            if isinstance(exc, UnauthorizedError)
            else 409
            if isinstance(exc, ConflictError)
            else 422
        )
        return JSONResponse(
            status_code=status_code,
            content={"detail": str(exc), "code": exc.__class__.__name__},
            headers={"WWW-Authenticate": "Bearer"} if isinstance(exc, UnauthorizedError) else None,
        )

    return app


app = create_app()
