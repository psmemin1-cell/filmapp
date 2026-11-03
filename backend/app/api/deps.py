"""FastAPI bağımlılıkları: lifespan'de kurulan nesneleri route'lara enjekte eder."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from fastapi import Request

from app.config import Settings
from app.core.cache import CacheBackend, InMemoryTTLCache
from app.services.aggregator import Aggregator
from app.services.dtdd_service import DTDDService
from app.services.movie_map_service import MovieMapService
from app.services.parents_guide.base import ParentsGuideProvider
from app.services.parents_guide.dataset import DatasetParentsGuideProvider, JsonlDatasetLookup
from app.services.parents_guide.scraper import ImdbScraperProvider
from app.services.tmdb_service import TMDBService


@dataclass(slots=True)
class AppContainer:
    settings: Settings
    http_client: httpx.AsyncClient
    cache: CacheBackend
    aggregator: Aggregator


def build_parents_guide_provider(
    settings: Settings, client: httpx.AsyncClient
) -> ParentsGuideProvider:
    if settings.parents_guide_provider == "dataset":
        lookup = (
            JsonlDatasetLookup(settings.parents_guide_dataset_path)
            if settings.parents_guide_dataset_path
            else None
        )
        return DatasetParentsGuideProvider(lookup)
    return ImdbScraperProvider(client, base_url=settings.imdb_base_url)


def build_container(
    settings: Settings,
    client: httpx.AsyncClient,
    cache: CacheBackend | None = None,
) -> AppContainer:
    if cache is None:
        cache = InMemoryTTLCache(maxsize=settings.cache_max_entries)
    tmdb = TMDBService(
        client,
        api_key=settings.tmdb_api_key.get_secret_value(),
        base_url=settings.tmdb_base_url,
        image_base_url=settings.tmdb_image_base_url,
        web_base_url=settings.tmdb_web_base_url,
    )
    dtdd = DTDDService(
        client,
        api_key=settings.dtdd_api_key.get_secret_value(),
        cache=cache,
        base_url=settings.dtdd_base_url,
        cache_ttl_seconds=settings.cache_ttl_seconds,
    )
    movie_map = MovieMapService(
        client, base_url=settings.movie_map_base_url, enabled=settings.enable_movie_map
    )
    aggregator = Aggregator(
        tmdb=tmdb,
        parents_guide=build_parents_guide_provider(settings, client),
        dtdd=dtdd,
        movie_map=movie_map,
        cache=cache,
        cache_ttl_seconds=settings.cache_ttl_seconds,
        degraded_cache_ttl_seconds=settings.degraded_cache_ttl_seconds,
        total_budget_seconds=settings.total_budget_seconds,
    )
    return AppContainer(settings=settings, http_client=client, cache=cache, aggregator=aggregator)


def get_container(request: Request) -> AppContainer:
    return request.app.state.container


def get_aggregator(request: Request) -> Aggregator:
    return get_container(request).aggregator
