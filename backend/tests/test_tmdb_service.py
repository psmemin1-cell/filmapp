from __future__ import annotations

import httpx
import pytest
import respx

from app.core.errors import MovieNotFound, SourceNotFound, SourceUnavailable
from app.services.tmdb_service import TMDBService
from tests.conftest import TMDB, load_json


@pytest.fixture
def tmdb(client: httpx.AsyncClient) -> TMDBService:
    return TMDBService(client, api_key="test-tmdb-key")


async def test_search_success_uses_tr_language(router: respx.MockRouter, tmdb: TMDBService) -> None:
    route = router.get(f"{TMDB}/search/movie").respond(
        json=load_json("tmdb_search_oppenheimer.json")
    )
    hit = await tmdb.search("oppenheimer")
    assert hit.tmdb_id == 872585
    params = route.calls.last.request.url.params
    assert params["language"] == "tr-TR"
    assert params["query"] == "oppenheimer"
    assert params["api_key"] == "test-tmdb-key"


async def test_search_prefers_exact_turkish_title(
    router: respx.MockRouter, tmdb: TMDBService
) -> None:
    router.get(f"{TMDB}/search/movie").respond(json=load_json("tmdb_search_lotr_tr.json"))
    hit = await tmdb.search("yuzuklerin efendisi")
    assert hit.tmdb_id == 1361  # katlanmış tam eşleşme ("Yüzüklerin Efendisi")
    hit = await tmdb.search("Yüzüklerin Efendisi Kralın Dönüşü")
    assert hit.tmdb_id == 122


async def test_search_partial_query_falls_back_to_relevance(
    router: respx.MockRouter, tmdb: TMDBService
) -> None:
    router.get(f"{TMDB}/search/movie").respond(json=load_json("tmdb_search_lotr_tr.json"))
    hit = await tmdb.search("yüzüklerin")
    assert hit.tmdb_id == 122  # tam eşleşme yok -> TMDB'nin ilk sonucu


async def test_search_not_found(router: respx.MockRouter, tmdb: TMDBService) -> None:
    router.get(f"{TMDB}/search/movie").respond(json=load_json("tmdb_search_empty.json"))
    with pytest.raises(MovieNotFound):
        await tmdb.search("asdfghjkl")


async def test_search_timeout(router: respx.MockRouter, tmdb: TMDBService) -> None:
    router.get(f"{TMDB}/search/movie").mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(SourceUnavailable):
        await tmdb.search("oppenheimer")


async def test_search_server_error(router: respx.MockRouter, tmdb: TMDBService) -> None:
    router.get(f"{TMDB}/search/movie").respond(status_code=500)
    with pytest.raises(SourceUnavailable):
        await tmdb.search("oppenheimer")


async def test_bearer_token_auth(router: respx.MockRouter, client: httpx.AsyncClient) -> None:
    route = router.get(f"{TMDB}/search/movie").respond(
        json=load_json("tmdb_search_oppenheimer.json")
    )
    service = TMDBService(client, api_key="eyJhbGciOiJIUzI1NiJ9.test")
    await service.search("oppenheimer")
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer eyJhbGciOiJIUzI1NiJ9.test"
    assert "api_key" not in request.url.params


async def test_missing_key_is_unavailable(client: httpx.AsyncClient) -> None:
    with pytest.raises(SourceUnavailable):
        await TMDBService(client, api_key="").search("x")


async def test_movie_details_single_call_with_external_ids(
    router: respx.MockRouter, tmdb: TMDBService
) -> None:
    router.get(f"{TMDB}/search/movie").respond(json=load_json("tmdb_search_oppenheimer.json"))
    route = router.get(f"{TMDB}/movie/872585").respond(json=load_json("tmdb_movie_872585.json"))
    movie = await tmdb.get_movie(await tmdb.search("oppenheimer"))
    assert route.calls.last.request.url.params["append_to_response"] == "external_ids"
    assert movie.imdb_id == "tt15398776"
    assert movie.runtime_minutes == 181
    assert movie.year == 2023
    assert movie.rating == 8.1
    assert movie.rating_source == "tmdb"
    assert movie.rating_votes == 7421
    assert movie.poster_url == "https://image.tmdb.org/t/p/w500/8Gxv8gSFCU0XGDykEGv7zR1n2ua.jpg"


async def test_movie_details_404(router: respx.MockRouter, tmdb: TMDBService) -> None:
    router.get(f"{TMDB}/search/movie").respond(json=load_json("tmdb_search_oppenheimer.json"))
    router.get(f"{TMDB}/movie/872585").respond(status_code=404)
    with pytest.raises(SourceNotFound):
        await tmdb.get_movie(await tmdb.search("oppenheimer"))


async def test_watch_providers_tr(router: respx.MockRouter, tmdb: TMDBService) -> None:
    router.get(f"{TMDB}/movie/872585/watch/providers").respond(
        json=load_json("tmdb_watch_providers_872585.json")
    )
    streaming = await tmdb.get_watch_providers(872585)
    assert streaming.available is True
    assert [p.name for p in streaming.flatrate] == ["Netflix"]
    assert streaming.flatrate[0].logo_url == (
        "https://image.tmdb.org/t/p/w92/pbpMk2JmcoNnQwx5JGpXngfoWtp.jpg"
    )
    assert [p.name for p in streaming.buy] == ["Apple TV", "Google Play Movies"]
    assert streaming.tmdb_link == "https://www.themoviedb.org/movie/872585/watch?locale=TR"


async def test_watch_providers_without_tr(router: respx.MockRouter, tmdb: TMDBService) -> None:
    router.get(f"{TMDB}/movie/872585/watch/providers").respond(
        json=load_json("tmdb_watch_providers_no_tr.json")
    )
    streaming = await tmdb.get_watch_providers(872585)
    assert streaming.available is False
    assert streaming.flatrate == streaming.rent == streaming.buy == []


async def test_watch_providers_timeout(router: respx.MockRouter, tmdb: TMDBService) -> None:
    router.get(f"{TMDB}/movie/872585/watch/providers").mock(side_effect=httpx.ConnectTimeout("x"))
    with pytest.raises(SourceUnavailable):
        await tmdb.get_watch_providers(872585)


async def test_recommendations_top5_excluding_self(
    router: respx.MockRouter, tmdb: TMDBService
) -> None:
    router.get(f"{TMDB}/movie/872585/recommendations").respond(
        json=load_json("tmdb_recommendations_872585.json")
    )
    similar = await tmdb.get_recommendations(872585)
    assert len(similar) == 5
    assert 872585 not in {m.tmdb_id for m in similar}
    assert similar[0].title == "Blade Runner 2049"
    assert similar[0].poster_url.startswith("https://image.tmdb.org/t/p/w342/")
    assert similar[0].rating == 7.6


async def test_recommendations_404(router: respx.MockRouter, tmdb: TMDBService) -> None:
    router.get(f"{TMDB}/movie/1/recommendations").respond(status_code=404)
    with pytest.raises(SourceNotFound):
        await tmdb.get_recommendations(1)
