from __future__ import annotations

import httpx
import pytest
import respx

from app.core.errors import SourceNotFound, SourceUnavailable
from app.services.movie_map_service import MovieMapService, parse_movie_map
from tests.conftest import MOVIE_MAP, load_text


def test_parse_excludes_searched_title() -> None:
    titles = parse_movie_map(load_text("movie_map_oppenheimer.html"), exclude_title="Oppenheimer")
    assert titles == ["Dunkirk", "Tenet", "The Prestige"]


async def test_disabled_by_default(client: httpx.AsyncClient) -> None:
    with pytest.raises(SourceUnavailable):
        await MovieMapService(client).similar_titles("Oppenheimer")


async def test_success(router: respx.MockRouter, client: httpx.AsyncClient) -> None:
    router.get(f"{MOVIE_MAP}/oppenheimer").respond(text=load_text("movie_map_oppenheimer.html"))
    service = MovieMapService(client, enabled=True)
    assert await service.similar_titles("Oppenheimer") == ["Dunkirk", "Tenet", "The Prestige"]


async def test_404(router: respx.MockRouter, client: httpx.AsyncClient) -> None:
    router.get(f"{MOVIE_MAP}/oppenheimer").respond(status_code=404)
    with pytest.raises(SourceNotFound):
        await MovieMapService(client, enabled=True).similar_titles("Oppenheimer")


async def test_timeout(router: respx.MockRouter, client: httpx.AsyncClient) -> None:
    router.get(f"{MOVIE_MAP}/oppenheimer").mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(SourceUnavailable):
        await MovieMapService(client, enabled=True).similar_titles("Oppenheimer")
