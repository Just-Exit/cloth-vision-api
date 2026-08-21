from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from cloth_vision_core import (
    AnalysisPipeline,
    MatchingEngine,
    PillowImageProcessor,
    RembgSegmentationProvider,
)
from cloth_vision_core.providers import OpenAIVisionProvider
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from cloth_vision_api.adapters.inbound.api.router import router
from cloth_vision_api.adapters.outbound.database import (
    SqlAlchemyIdentityRepository,
    SqlAlchemyWardrobeRepository,
    create_session_factory,
    upgrade_database,
)
from cloth_vision_api.adapters.outbound.security import Argon2PasswordManager, JwtTokenManager
from cloth_vision_api.adapters.outbound.storage import LocalImageStorage
from cloth_vision_api.application.errors import (
    ApplicationError,
    ConflictError,
    NotFoundError,
    UnauthorizedError,
)
from cloth_vision_api.application.identity import AuthService
from cloth_vision_api.application.wardrobe import ClosetService
from cloth_vision_api.config import Settings

access_logger = logging.getLogger("cloth_vision_api.access")
access_logger.setLevel(logging.INFO)


def create_app(settings: Settings | None = None) -> FastAPI:
    config = settings or Settings()
    Path("./var").mkdir(parents=True, exist_ok=True)
    session_factory = create_session_factory(config.database_url)
    identity_repository = SqlAlchemyIdentityRepository(session_factory)
    wardrobe_repository = SqlAlchemyWardrobeRepository(session_factory)
    vision_provider = (
        OpenAIVisionProvider(
            model=config.openai_vision_model,
            api_key=config.openai_api_key.get_secret_value(),
        )
        if config.openai_api_key
        else None
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        if config.run_database_migrations:
            upgrade_database(config.database_url)
        # Alembic's logging configuration can disable loggers created before migration startup.
        access_logger.disabled = False
        access_logger.setLevel(logging.INFO)
        yield

    app = FastAPI(
        title=config.app_name,
        version="0.1.0",
        description="cloth-vision backend",
        lifespan=lifespan,
    )
    app.state.settings = config
    app.state.closet_service = ClosetService(
        identity_repository,
        wardrobe_repository,
        LocalImageStorage(config.upload_dir),
        AnalysisPipeline(
            PillowImageProcessor(),
            vision_provider,
            RembgSegmentationProvider(model=config.segmentation_model)
            if config.enable_segmentation
            else None,
        ),
        MatchingEngine(),
    )
    app.state.auth_service = AuthService(
        identity_repository,
        Argon2PasswordManager(),
        JwtTokenManager(
            config.jwt_secret_key,
            config.jwt_algorithm,
            config.access_token_expire_minutes,
        ),
    )
    app.include_router(router)

    @app.middleware("http")
    async def access_log(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex}"
        started_at = perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = (perf_counter() - started_at) * 1000
            access_logger.info(
                "%s %s status=%d duration_ms=%.1f request_id=%s",
                request.method,
                request.url.path,
                status_code,
                duration_ms,
                request_id,
            )

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
