from __future__ import annotations

import time
from collections.abc import AsyncIterator, Callable

import httpx
import pytest
import respx
from fastapi import FastAPI

from app.api.deps import build_container
from app.config import Settings
from app.core.cache import InMemoryTTLCache
from app.main import create_app
from tests.conftest import TMDB, load_json


@pytest.fixture
async def api(
    settings: Settings, client: httpx.AsyncClient
) -> AsyncIterator[tuple[FastAPI, httpx.AsyncClient]]:
    app = create_app(settings)
    # Lifespan yerine test client'ı ve izole cache'i enjekte et.
    app.state.container = build_container(settings, client, InMemoryTTLCache())
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield app, http


@pytest.fixture
def router_passthrough_testserver(router: respx.MockRouter) -> respx.MockRouter:
    router.route(host="testserver").pass_through()
    return router


async def test_search_200_contract_shape(
    mock_all_happy: Callable[[], None],
    router_passthrough_testserver: respx.MockRouter,
    api: tuple[FastAPI, httpx.AsyncClient],
) -> None:
    mock_all_happy()
    _, http = api
    response = await http.get("/api/v1/movies/search", params={"title": "Oppenheimer"})
    assert response.status_code == 200
    body = response.json()
    assert set(body) == {
        "query",
        "movie",
        "streaming_tr",
        "content_advisory",
        "similar",
        "sources",
        "cached",
        "generated_at",
    }
    assert body["movie"]["rating_source"] == "tmdb"
    assert body["generated_at"].endswith("Z")
    breakdown = body["content_advisory"]["sex_nudity"]["vote_breakdown"]
    assert abs(sum(breakdown.values()) - 1.0) <= 0.01
    assert body["content_advisory"]["attribution"] == "Powered by DoesTheDogDie.com"


async def test_search_404_body(
    router_passthrough_testserver: respx.MockRouter,
    api: tuple[FastAPI, httpx.AsyncClient],
) -> None:
    router_passthrough_testserver.get(f"{TMDB}/search/movie").respond(
        json=load_json("tmdb_search_empty.json")
    )
    _, http = api
    response = await http.get("/api/v1/movies/search", params={"title": "Asdfghjkl Qwerty"})
    assert response.status_code == 404
    assert response.json() == {"detail": "movie_not_found", "query": "asdfghjkl qwerty"}


async def test_search_503_when_tmdb_down(
    router_passthrough_testserver: respx.MockRouter,
    api: tuple[FastAPI, httpx.AsyncClient],
) -> None:
    router_passthrough_testserver.get(f"{TMDB}/search/movie").mock(
        side_effect=httpx.ConnectError("down")
    )
    _, http = api
    response = await http.get("/api/v1/movies/search", params={"title": "Oppenheimer"})
    assert response.status_code == 503
    assert response.json()["detail"] == "upstream_unavailable"


@pytest.mark.parametrize("title", ["", "   "])
async def test_search_422_empty(
    router_passthrough_testserver: respx.MockRouter,
    api: tuple[FastAPI, httpx.AsyncClient],
    title: str,
) -> None:
    _, http = api
    response = await http.get("/api/v1/movies/search", params={"title": title})
    assert response.status_code == 422


async def test_turkish_query_is_passed_through(
    mock_all_happy: Callable[[], None],
    router_passthrough_testserver: respx.MockRouter,
    api: tuple[FastAPI, httpx.AsyncClient],
) -> None:
    mock_all_happy()
    _, http = api
    response = await http.get("/api/v1/movies/search", params={"title": "Yüzüklerin Efendisi"})
    assert response.status_code == 200
    search_call = next(
        c for c in router_passthrough_testserver.calls if c.request.url.path == "/3/search/movie"
    )
    assert search_call.request.url.params["query"] == "yüzüklerin efendisi"


async def test_cached_second_call_under_200ms(
    mock_all_happy: Callable[[], None],
    router_passthrough_testserver: respx.MockRouter,
    api: tuple[FastAPI, httpx.AsyncClient],
) -> None:
    mock_all_happy()
    _, http = api
    first = await http.get("/api/v1/movies/search", params={"title": "Oppenheimer"})
    assert first.json()["cached"] is False
    started = time.perf_counter()
    second = await http.get("/api/v1/movies/search", params={"title": "oppenheimer"})
    elapsed_ms = (time.perf_counter() - started) * 1000
    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert elapsed_ms < 200


async def test_openapi_and_docs(
    router_passthrough_testserver: respx.MockRouter,
    api: tuple[FastAPI, httpx.AsyncClient],
) -> None:
    _, http = api
    schema = (await http.get("/openapi.json")).json()
    assert "/api/v1/movies/search" in schema["paths"]
    assert "MovieSearchResponse" in schema["components"]["schemas"]
    docs = await http.get("/docs")
    assert docs.status_code == 200
    assert (await http.get("/health")).json() == {"status": "ok"}
