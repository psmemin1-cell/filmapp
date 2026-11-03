"""CineScope FastAPI uygulaması."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.deps import build_container
from app.api.v1.routes import router as v1_router
from app.config import Settings, get_settings
from app.core.http import create_http_client
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        client = create_http_client(settings.request_timeout_seconds)
        app.state.container = build_container(settings, client)
        if not settings.tmdb_api_key.get_secret_value():
            logger.warning("tmdb_api_key_missing")
        if not settings.dtdd_api_key.get_secret_value():
            logger.warning("dtdd_api_key_missing")
        logger.info(
            "startup",
            extra={
                "parents_guide_provider": settings.parents_guide_provider,
                "movie_map_enabled": settings.enable_movie_map,
            },
        )
        try:
            yield
        finally:
            await client.aclose()

    app = FastAPI(
        title="CineScope API",
        version="1.0.0",
        description=(
            "Film puanı, Türkiye yayın platformları, içerik hassasiyeti raporu ve benzer "
            "film önerileri. Topluluk verisi: Powered by DoesTheDogDie.com"
        ),
        lifespan=lifespan,
    )
    origins = settings.cors_origins
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=False,
            allow_methods=["GET"],
            allow_headers=["*"],
        )
    app.include_router(v1_router)

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
