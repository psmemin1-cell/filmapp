"""v1 HTTP uç noktaları."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from app.api.deps import get_aggregator
from app.core.errors import MovieNotFound, SourceError
from app.core.text import normalize_title
from app.schemas.movie_response import (
    MovieNotFoundBody,
    MovieSearchResponse,
    UpstreamUnavailableBody,
)
from app.services.aggregator import Aggregator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["movies"])


@router.get(
    "/movies/search",
    response_model=MovieSearchResponse,
    summary="Film ara: künye, TR yayın platformları, içerik hassasiyeti, benzer filmler",
    responses={
        404: {"model": MovieNotFoundBody, "description": "TMDB'de film bulunamadı"},
        503: {"model": UpstreamUnavailableBody, "description": "TMDB'ye ulaşılamadı"},
    },
)
async def search_movie(
    title: Annotated[str, Query(min_length=1, max_length=200, description="Film adı")],
    aggregator: Annotated[Aggregator, Depends(get_aggregator)],
) -> MovieSearchResponse | JSONResponse:
    query = normalize_title(title)
    if not query:
        return JSONResponse(status_code=422, content={"detail": "empty_query", "query": title})
    try:
        return await aggregator.search(query)
    except MovieNotFound:
        logger.info("movie_not_found", extra={"query": query})
        return JSONResponse(status_code=404, content=MovieNotFoundBody(query=query).model_dump())
    except SourceError as exc:
        logger.warning("tmdb_unavailable", extra={"query": query, "reason": exc.reason})
        return JSONResponse(
            status_code=503, content=UpstreamUnavailableBody(query=query).model_dump()
        )
