from __future__ import annotations

import asyncio
from collections.abc import Callable

import httpx
import pytest
import respx

from app.api.deps import build_container
from app.config import Settings
from app.core.cache import InMemoryTTLCache
from app.core.errors import MovieNotFound, SourceUnavailable
from app.services.aggregator import Aggregator
from tests.conftest import (
    DTDD,
    IMDB,
    MOVIE_MAP,
    TMDB,
    load_json,
    load_text,
    mock_dtdd_happy,
    mock_imdb_happy,
    mock_tmdb_happy,
)


def make(settings: Settings, client: httpx.AsyncClient, cache: InMemoryTTLCache) -> Aggregator:
    return build_container(settings, client, cache).aggregator


async def test_all_sources_ok(
    mock_all_happy: Callable[[], None],
    settings: Settings,
    client: httpx.AsyncClient,
    cache: InMemoryTTLCache,
) -> None:
    mock_all_happy()
    response = await make(settings, client, cache).search("  Oppenheimer ")

    assert response.query == "oppenheimer"
    assert response.cached is False
    assert response.sources.model_dump() == {
        "tmdb": "ok",
        "imdb_parents_guide": "ok",
        "dtdd": "ok",
        "similar": "ok",
    }
    assert response.movie.imdb_id == "tt15398776"
    assert response.streaming_tr is not None and response.streaming_tr.available
    advisory = response.content_advisory
    assert advisory is not None
    assert advisory.sex_nudity is not None and advisory.sex_nudity.severity == "Moderate"
    assert advisory.sex_nudity.vote_total == 412
    assert [c.name for c in advisory.other_categories or []] == [
        "Violence & Gore",
        "Profanity",
        "Alcohol, Drugs & Smoking",
        "Frightening & Intense Scenes",
    ]
    assert advisory.community and advisory.community[0].topic_key == "nudity"
    assert advisory.attribution == "Powered by DoesTheDogDie.com"
    assert response.similar is not None and len(response.similar) == 5


async def test_three_of_four_sources_down_still_returns(
    router: respx.MockRouter,
    settings: Settings,
    client: httpx.AsyncClient,
    cache: InMemoryTTLCache,
) -> None:
    router.get(f"{TMDB}/search/movie").respond(json=load_json("tmdb_search_oppenheimer.json"))
    router.get(f"{TMDB}/movie/872585").respond(json=load_json("tmdb_movie_872585.json"))
    router.get(f"{TMDB}/movie/872585/watch/providers").respond(
        json=load_json("tmdb_watch_providers_872585.json")
    )
    router.get(f"{TMDB}/movie/872585/recommendations").respond(status_code=500)
    router.get(f"{IMDB}/title/tt15398776/parentalguide/").respond(status_code=403)
    router.get(f"{DTDD}/topics").mock(side_effect=httpx.ConnectError("down"))

    response = await make(settings, client, cache).search("oppenheimer")

    assert response.sources.model_dump() == {
        "tmdb": "ok",
        "imdb_parents_guide": "unavailable",
        "dtdd": "unavailable",
        "similar": "unavailable",
    }
    assert response.movie.title == "Oppenheimer"
    assert response.streaming_tr is not None
    assert response.content_advisory is None
    assert response.similar is None


async def test_parents_guide_missing_keeps_community(
    router: respx.MockRouter,
    settings: Settings,
    client: httpx.AsyncClient,
    cache: InMemoryTTLCache,
) -> None:
    mock_tmdb_happy(router)
    mock_dtdd_happy(router)
    router.get(f"{IMDB}/title/tt15398776/parentalguide/").respond(
        text=load_text("imdb_waf_challenge.html"), headers={"x-amzn-waf-action": "challenge"}
    )
    response = await make(settings, client, cache).search("oppenheimer")
    assert response.sources.imdb_parents_guide == "unavailable"
    assert response.sources.dtdd == "ok"
    advisory = response.content_advisory
    assert advisory is not None
    assert advisory.sex_nudity is None and advisory.other_categories is None
    assert advisory.community


async def test_dtdd_not_found_keeps_parents_guide(
    router: respx.MockRouter,
    settings: Settings,
    client: httpx.AsyncClient,
    cache: InMemoryTTLCache,
) -> None:
    mock_tmdb_happy(router)
    mock_imdb_happy(router)
    router.get(f"{DTDD}/topics").respond(json=load_json("dtdd_topics.json"))
    router.get(f"{DTDD}/items").respond(json=load_json("dtdd_items_empty.json"))
    response = await make(settings, client, cache).search("oppenheimer")
    assert response.sources.dtdd == "not_found"
    assert response.content_advisory is not None
    assert response.content_advisory.community is None
    assert response.content_advisory.sex_nudity is not None


async def test_not_in_turkey_streaming(
    router: respx.MockRouter,
    settings: Settings,
    client: httpx.AsyncClient,
    cache: InMemoryTTLCache,
) -> None:
    mock_tmdb_happy(router)
    mock_imdb_happy(router)
    mock_dtdd_happy(router)
    router.get(f"{TMDB}/movie/872585/watch/providers").respond(
        json=load_json("tmdb_watch_providers_no_tr.json")
    )
    response = await make(settings, client, cache).search("oppenheimer")
    assert response.streaming_tr is not None
    assert response.streaming_tr.available is False


async def test_tmdb_not_found_raises(
    router: respx.MockRouter,
    settings: Settings,
    client: httpx.AsyncClient,
    cache: InMemoryTTLCache,
) -> None:
    router.get(f"{TMDB}/search/movie").respond(json=load_json("tmdb_search_empty.json"))
    with pytest.raises(MovieNotFound):
        await make(settings, client, cache).search("asdfghjkl")


async def test_tmdb_down_raises(
    router: respx.MockRouter,
    settings: Settings,
    client: httpx.AsyncClient,
    cache: InMemoryTTLCache,
) -> None:
    router.get(f"{TMDB}/search/movie").respond(status_code=503)
    with pytest.raises(SourceUnavailable):
        await make(settings, client, cache).search("oppenheimer")


async def test_details_failure_falls_back_to_search_hit(
    router: respx.MockRouter,
    settings: Settings,
    client: httpx.AsyncClient,
    cache: InMemoryTTLCache,
) -> None:
    mock_tmdb_happy(router)
    router.get(f"{TMDB}/movie/872585").respond(status_code=500)
    response = await make(settings, client, cache).search("oppenheimer")
    assert response.movie.tmdb_id == 872585
    assert response.movie.imdb_id is None
    # imdb_id yoksa IMDb ve DTDD filmi tanıyamaz -> not_found
    assert response.sources.imdb_parents_guide == "not_found"
    assert response.sources.dtdd == "not_found"


async def test_budget_exhausted_returns_what_it_has(
    router: respx.MockRouter,
    client: httpx.AsyncClient,
    cache: InMemoryTTLCache,
) -> None:
    settings = Settings(
        _env_file=None,
        tmdb_api_key="k",
        dtdd_api_key="k",
        total_budget_seconds=0.3,
    )
    mock_tmdb_happy(router)
    mock_dtdd_happy(router)

    async def slow(_request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(2)
        return httpx.Response(200, text=load_text("imdb_parentalguide_tt15398776.html"))

    router.get(f"{IMDB}/title/tt15398776/parentalguide/").mock(side_effect=slow)
    started = asyncio.get_running_loop().time()
    response = await make(settings, client, cache).search("oppenheimer")
    assert asyncio.get_running_loop().time() - started < 1.5
    assert response.sources.imdb_parents_guide == "unavailable"
    assert response.sources.dtdd == "ok"


async def test_second_search_served_from_cache(
    mock_all_happy: Callable[[], None],
    router: respx.MockRouter,
    settings: Settings,
    client: httpx.AsyncClient,
    cache: InMemoryTTLCache,
) -> None:
    mock_all_happy()
    aggregator = make(settings, client, cache)
    first = await aggregator.search("Oppenheimer")
    calls = len(router.calls)

    second = await aggregator.search("OPPENHEIMER  ")
    assert second.cached is True
    assert len(router.calls) == calls
    assert second.movie == first.movie
    assert second.generated_at == first.generated_at


async def test_different_query_same_movie_hits_movie_cache(
    mock_all_happy: Callable[[], None],
    router: respx.MockRouter,
    settings: Settings,
    client: httpx.AsyncClient,
    cache: InMemoryTTLCache,
) -> None:
    mock_all_happy()
    aggregator = make(settings, client, cache)
    await aggregator.search("oppenheimer")
    imdb_calls = router.routes  # sadece arama yeniden yapılır
    response = await aggregator.search("oppenheimer 2023")
    assert response.cached is True
    searches = [c for c in router.calls if c.request.url.path == "/3/search/movie"]
    assert len(searches) == 2
    assert imdb_calls


async def test_degraded_response_gets_short_ttl(
    router: respx.MockRouter,
    settings: Settings,
    client: httpx.AsyncClient,
) -> None:
    class RecordingCache(InMemoryTTLCache):
        def __init__(self) -> None:
            super().__init__()
            self.ttls: dict[str, int] = {}

        async def set(self, key: str, value: object, ttl_seconds: int) -> None:
            self.ttls[key] = ttl_seconds
            await super().set(key, value, ttl_seconds)

    cache = RecordingCache()
    mock_tmdb_happy(router)
    mock_imdb_happy(router)
    router.get(f"{DTDD}/topics").respond(status_code=500)
    await make(settings, cache=cache, client=client).search("oppenheimer")
    assert cache.ttls["search:oppenheimer"] == settings.degraded_cache_ttl_seconds


async def test_concurrent_identical_requests_coalesced(
    mock_all_happy: Callable[[], None],
    router: respx.MockRouter,
    settings: Settings,
    client: httpx.AsyncClient,
    cache: InMemoryTTLCache,
) -> None:
    mock_all_happy()
    aggregator = make(settings, client, cache)
    await asyncio.gather(aggregator.search("oppenheimer"), aggregator.search("Oppenheimer"))
    detail_calls = [c for c in router.calls if c.request.url.path == "/api/v3/items/1013637"]
    assert len(detail_calls) == 1


async def test_movie_map_fallback_when_recommendations_empty(
    router: respx.MockRouter,
    client: httpx.AsyncClient,
    cache: InMemoryTTLCache,
) -> None:
    settings = Settings(_env_file=None, tmdb_api_key="k", dtdd_api_key="k", enable_movie_map=True)
    mock_tmdb_happy(router)
    mock_imdb_happy(router)
    mock_dtdd_happy(router)
    router.get(f"{TMDB}/movie/872585/recommendations").respond(
        json=load_json("tmdb_recommendations_empty.json")
    )
    router.get(f"{MOVIE_MAP}/oppenheimer").respond(text=load_text("movie_map_oppenheimer.html"))
    recs = {r["title"]: r for r in load_json("tmdb_recommendations_872585.json")["results"]}

    def search(request: httpx.Request) -> httpx.Response:
        query = request.url.params["query"]
        if query == "oppenheimer":
            return httpx.Response(200, json=load_json("tmdb_search_oppenheimer.json"))
        hit = recs.get(query)
        return httpx.Response(200, json={"results": [hit] if hit else []})

    router.get(f"{TMDB}/search/movie").mock(side_effect=search)
    response = await make(settings, client, cache).search("oppenheimer")
    assert response.sources.similar == "fallback"
    # Movie-Map: Dunkirk, Tenet, The Prestige -> TMDB'de çözülebilenler (fixture: Dunkirk, Tenet)
    assert [m.tmdb_id for m in response.similar or []] == [374720, 577922]


async def test_recommendations_empty_without_movie_map_is_not_found(
    router: respx.MockRouter,
    settings: Settings,
    client: httpx.AsyncClient,
    cache: InMemoryTTLCache,
) -> None:
    mock_tmdb_happy(router)
    mock_imdb_happy(router)
    mock_dtdd_happy(router)
    router.get(f"{TMDB}/movie/872585/recommendations").respond(
        json=load_json("tmdb_recommendations_empty.json")
    )
    response = await make(settings, client, cache).search("oppenheimer")
    assert response.sources.similar == "not_found"
    assert response.similar is None


async def test_movie_map_failure_falls_back_silently(
    router: respx.MockRouter,
    client: httpx.AsyncClient,
    cache: InMemoryTTLCache,
) -> None:
    settings = Settings(_env_file=None, tmdb_api_key="k", dtdd_api_key="k", enable_movie_map=True)
    mock_tmdb_happy(router)
    mock_imdb_happy(router)
    mock_dtdd_happy(router)
    router.get(f"{MOVIE_MAP}/oppenheimer").respond(status_code=500)
    response = await make(settings, client, cache).search("oppenheimer")
    # TMDB önerileri dolu -> Movie-Map hiç denenmez, sonuç "ok"
    assert response.sources.similar == "ok"
