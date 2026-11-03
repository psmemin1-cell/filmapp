"""Ortak test fixture'ları. Hiçbir test gerçek ağa çıkmaz (respx assert_all_mocked)."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx

from app.config import Settings
from app.core.cache import InMemoryTTLCache

FIXTURES = Path(__file__).parent / "fixtures"

TMDB = "https://api.themoviedb.org/3"
IMDB = "https://www.imdb.com"
DTDD = "https://www.doesthedogdie.com/api/v3"
MOVIE_MAP = "https://www.movie-map.com"


def load_json(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def load_text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@pytest.fixture
def settings() -> Settings:
    return Settings(
        _env_file=None,
        tmdb_api_key="test-tmdb-key",
        dtdd_api_key="test-dtdd-key",
        enable_movie_map=False,
        log_level="WARNING",
        request_timeout_seconds=6.0,
        total_budget_seconds=12.0,
    )


@pytest.fixture
def router() -> AsyncIterator[respx.MockRouter]:
    # assert_all_mocked: mock'lanmamış bir URL'ye istek atılırsa test patlar -> gerçek ağ yok.
    with respx.mock(assert_all_called=False, assert_all_mocked=True) as mock:
        yield mock


@pytest.fixture
async def client(router: respx.MockRouter) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(timeout=6.0, follow_redirects=True) as http:
        yield http


@pytest.fixture
def cache() -> InMemoryTTLCache:
    return InMemoryTTLCache()


def mock_tmdb_happy(router: respx.MockRouter) -> None:
    router.get(f"{TMDB}/search/movie").respond(json=load_json("tmdb_search_oppenheimer.json"))
    router.get(f"{TMDB}/movie/872585").respond(json=load_json("tmdb_movie_872585.json"))
    router.get(f"{TMDB}/movie/872585/watch/providers").respond(
        json=load_json("tmdb_watch_providers_872585.json")
    )
    router.get(f"{TMDB}/movie/872585/recommendations").respond(
        json=load_json("tmdb_recommendations_872585.json")
    )


def mock_imdb_happy(router: respx.MockRouter) -> None:
    router.get(f"{IMDB}/title/tt15398776/parentalguide/").respond(
        text=load_text("imdb_parentalguide_tt15398776.html"),
        headers={"content-type": "text/html; charset=utf-8"},
    )


def mock_dtdd_happy(router: respx.MockRouter) -> None:
    router.get(f"{DTDD}/topics").respond(json=load_json("dtdd_topics.json"))
    router.get(f"{DTDD}/items", params={"imdb": "tt15398776"}).respond(
        json=load_json("dtdd_items_by_imdb.json")
    )
    router.get(f"{DTDD}/items/1013637").respond(json=load_json("dtdd_item_detail.json"))
    for topic_id in (108, 153, 175):
        router.get(f"{DTDD}/items/1013637/ratings", params={"topicId": str(topic_id)}).respond(
            json=load_json(f"dtdd_ratings_{topic_id}.json")
        )


@pytest.fixture
def mock_all_happy(router: respx.MockRouter) -> Callable[[], None]:
    def apply() -> None:
        mock_tmdb_happy(router)
        mock_imdb_happy(router)
        mock_dtdd_happy(router)

    return apply
