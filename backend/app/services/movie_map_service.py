"""Movie-Map benzer film kaynağı (deneysel, ENABLE_MOVIE_MAP=false varsayılan).

Movie-Map sayfası haritayı istemci tarafında JS ile çizer; sunucu tarafı istekle
güvenilir veri çıkmayabilir. Bu yüzden yalnızca TMDB önerileri boş/düşük olduğunda
ikincil kaynak olarak denenir ve her hata sessizce SourceUnavailable'a çevrilir.

Varsayım (doğrulanamadı): sayfa https://www.movie-map.com/{başlık+kelimeleri} adresinde
ve öneriler `#gnodMap a` bağlantılarında (ilk bağlantı aranan filmin kendisi).
"""

from __future__ import annotations

import logging
from urllib.parse import quote_plus

import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser

from app.core.errors import SourceNotFound, SourceUnavailable
from app.core.text import fold_title

logger = logging.getLogger(__name__)

SOURCE = "movie_map"


def parse_movie_map(html: str, exclude_title: str, limit: int = 5) -> list[str]:
    tree = HTMLParser(html)
    excluded = fold_title(exclude_title)
    titles: list[str] = []
    seen: set[str] = {excluded}
    for anchor in tree.css("#gnodMap a"):
        title = anchor.text(strip=True)
        folded = fold_title(title)
        if not title or folded in seen:
            continue
        seen.add(folded)
        titles.append(title)
        if len(titles) == limit:
            break
    return titles


class MovieMapService:
    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str = "https://www.movie-map.com",
        enabled: bool = False,
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self.enabled = enabled

    async def similar_titles(self, title: str, limit: int = 5) -> list[str]:
        if not self.enabled:
            raise SourceUnavailable(SOURCE, "disabled")
        url = f"{self._base_url}/{quote_plus(title.lower())}"
        try:
            response = await self._client.get(url, headers={"Accept": "text/html"})
        except httpx.HTTPError as exc:
            raise SourceUnavailable(SOURCE, f"transport {type(exc).__name__}") from exc
        if response.status_code == 404:
            raise SourceNotFound(SOURCE, "http 404")
        if response.status_code != 200:
            raise SourceUnavailable(SOURCE, f"http {response.status_code}")
        titles = parse_movie_map(response.text, exclude_title=title, limit=limit)
        if not titles:
            raise SourceNotFound(SOURCE, "no_titles")
        return titles
