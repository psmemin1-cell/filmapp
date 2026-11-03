"""TMDB API v3 istemcisi.

Kullanılan uç noktalar (doğrulanmış):
  /search/movie?query=&language=tr-TR
  /movie/{id}?append_to_response=external_ids
  /movie/{id}/watch/providers        -> results.TR.{flatrate,rent,buy}
  /movie/{id}/recommendations
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.errors import MovieNotFound, SourceNotFound, SourceUnavailable
from app.core.text import fold_title
from app.schemas.movie_response import Movie, Provider, SimilarMovie, StreamingTR

logger = logging.getLogger(__name__)

SOURCE = "tmdb"
LANGUAGE = "tr-TR"
REGION = "TR"
POSTER_SIZE = "w500"
SIMILAR_POSTER_SIZE = "w342"
LOGO_SIZE = "w92"
SIMILAR_LIMIT = 5


@dataclass(slots=True)
class SearchHit:
    tmdb_id: int
    title: str
    original_title: str | None
    release_date: str | None
    poster_path: str | None
    overview: str
    vote_average: float | None
    vote_count: int | None


def _year(release_date: str | None) -> int | None:
    if release_date and len(release_date) >= 4 and release_date[:4].isdigit():
        return int(release_date[:4])
    return None


def _rating(value: Any) -> float | None:
    if isinstance(value, int | float) and value > 0:
        return round(float(value), 1)
    return None


class TMDBService:
    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        base_url: str = "https://api.themoviedb.org/3",
        image_base_url: str = "https://image.tmdb.org/t/p",
        web_base_url: str = "https://www.themoviedb.org",
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._image_base_url = image_base_url.rstrip("/")
        self._web_base_url = web_base_url.rstrip("/")

    # ------------------------------------------------------------------ helpers
    def _auth(self) -> tuple[dict[str, str], dict[str, str]]:
        """v4 okuma token'ı (JWT, 'eyJ' ile başlar) Bearer olarak, v3 anahtarı query'de."""
        if self._api_key.startswith("eyJ"):
            return {"Authorization": f"Bearer {self._api_key}"}, {}
        return {}, {"api_key": self._api_key}

    def image_url(self, path: str | None, size: str) -> str | None:
        return f"{self._image_base_url}/{size}{path}" if path else None

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._api_key:
            raise SourceUnavailable(SOURCE, "missing_api_key")
        headers, auth_params = self._auth()
        try:
            response = await self._client.get(
                f"{self._base_url}{path}",
                params={**(params or {}), **auth_params},
                headers=headers,
            )
        except httpx.TimeoutException as exc:
            raise SourceUnavailable(SOURCE, f"timeout {path}") from exc
        except httpx.HTTPError as exc:
            raise SourceUnavailable(SOURCE, f"transport {type(exc).__name__}") from exc

        if response.status_code == 404:
            raise SourceNotFound(SOURCE, path)
        if response.status_code != 200:
            raise SourceUnavailable(SOURCE, f"http {response.status_code} {path}")
        try:
            data = response.json()
        except ValueError as exc:
            raise SourceUnavailable(SOURCE, "invalid_json") from exc
        if not isinstance(data, dict):
            raise SourceUnavailable(SOURCE, "unexpected_payload")
        return data

    # ------------------------------------------------------------------ search
    async def search(self, query: str) -> SearchHit:
        """En iyi eşleşmeyi döndürür; sonuç yoksa MovieNotFound."""
        data = await self._get(
            "/search/movie",
            {"query": query, "language": LANGUAGE, "include_adult": "false"},
        )
        results = [r for r in data.get("results") or [] if isinstance(r, dict) and r.get("id")]
        if not results:
            raise MovieNotFound(query)
        best = self._pick_best(query, results)
        return SearchHit(
            tmdb_id=int(best["id"]),
            title=best.get("title") or best.get("original_title") or query,
            original_title=best.get("original_title"),
            release_date=best.get("release_date") or None,
            poster_path=best.get("poster_path"),
            overview=best.get("overview") or "",
            vote_average=best.get("vote_average"),
            vote_count=best.get("vote_count"),
        )

    @staticmethod
    def _pick_best(query: str, results: list[dict[str, Any]]) -> dict[str, Any]:
        """TMDB alaka sırasını korur; ilk 5 içinde tam başlık eşleşmesi varsa onu seçer.

        Karşılaştırma Türkçe karakter katlanarak yapılır ("yuzuklerin efendisi" ==
        "Yüzüklerin Efendisi"). Eşit eşleşmelerde oy sayısı fazla olan kazanır.
        """
        folded_query = fold_title(query)
        exact = [
            r
            for r in results[:5]
            if folded_query
            in {fold_title(r.get("title") or ""), fold_title(r.get("original_title") or "")}
        ]
        if exact:
            return max(exact, key=lambda r: r.get("vote_count") or 0)
        return results[0]

    # ------------------------------------------------------------------ details
    async def get_movie(self, hit: SearchHit) -> Movie:
        """Künye: imdb_id ve runtime için tek çağrı (append_to_response=external_ids)."""
        data = await self._get(
            f"/movie/{hit.tmdb_id}",
            {"language": LANGUAGE, "append_to_response": "external_ids"},
        )
        external = data.get("external_ids") or {}
        imdb_id = external.get("imdb_id") or data.get("imdb_id") or None
        runtime = data.get("runtime")
        release_date = data.get("release_date") or hit.release_date
        return Movie(
            tmdb_id=hit.tmdb_id,
            imdb_id=imdb_id,
            title=data.get("title") or hit.title,
            original_title=data.get("original_title") or hit.original_title,
            year=_year(release_date),
            runtime_minutes=runtime if isinstance(runtime, int) and runtime > 0 else None,
            overview=data.get("overview") or hit.overview,
            poster_url=self.image_url(data.get("poster_path") or hit.poster_path, POSTER_SIZE),
            rating=_rating(data.get("vote_average", hit.vote_average)),
            rating_source="tmdb",
            rating_votes=data.get("vote_count", hit.vote_count),
        )

    def movie_from_hit(self, hit: SearchHit) -> Movie:
        """Detay çağrısı düşerse aramadan gelen alanlarla asgari künye."""
        return Movie(
            tmdb_id=hit.tmdb_id,
            title=hit.title,
            original_title=hit.original_title,
            year=_year(hit.release_date),
            overview=hit.overview,
            poster_url=self.image_url(hit.poster_path, POSTER_SIZE),
            rating=_rating(hit.vote_average),
            rating_votes=hit.vote_count,
        )

    # ------------------------------------------------------------------ providers
    def watch_link(self, tmdb_id: int) -> str:
        return f"{self._web_base_url}/movie/{tmdb_id}/watch?locale={REGION}"

    async def get_watch_providers(self, tmdb_id: int) -> StreamingTR:
        data = await self._get(f"/movie/{tmdb_id}/watch/providers")
        tr = (data.get("results") or {}).get(REGION)
        link = self.watch_link(tmdb_id)
        if not tr:
            return StreamingTR(available=False, tmdb_link=link)

        def providers(kind: str) -> list[Provider]:
            out: list[Provider] = []
            seen: set[str] = set()
            for item in tr.get(kind) or []:
                name = (item or {}).get("provider_name")
                if not name or name in seen:
                    continue
                seen.add(name)
                out.append(
                    Provider(name=name, logo_url=self.image_url(item.get("logo_path"), LOGO_SIZE))
                )
            return out

        flatrate, rent, buy = providers("flatrate"), providers("rent"), providers("buy")
        return StreamingTR(
            available=bool(flatrate or rent or buy),
            flatrate=flatrate,
            rent=rent,
            buy=buy,
            tmdb_link=link,
        )

    # ------------------------------------------------------------------ similar
    async def get_recommendations(self, tmdb_id: int) -> list[SimilarMovie]:
        data = await self._get(f"/movie/{tmdb_id}/recommendations", {"language": LANGUAGE})
        out: list[SimilarMovie] = []
        for r in data.get("results") or []:
            if not isinstance(r, dict) or not r.get("id") or int(r["id"]) == tmdb_id:
                continue
            out.append(self._similar_from_result(r))
            if len(out) == SIMILAR_LIMIT:
                break
        return out

    async def search_similar_candidate(self, title: str) -> SimilarMovie | None:
        """Movie-Map'ten gelen başlığı TMDB kaydına çözer (yalnızca feature flag açıkken)."""
        data = await self._get(
            "/search/movie", {"query": title, "language": LANGUAGE, "include_adult": "false"}
        )
        results = [r for r in data.get("results") or [] if isinstance(r, dict) and r.get("id")]
        if not results:
            return None
        return self._similar_from_result(self._pick_best(title, results))

    def _similar_from_result(self, r: dict[str, Any]) -> SimilarMovie:
        return SimilarMovie(
            tmdb_id=int(r["id"]),
            title=r.get("title") or r.get("original_title") or "",
            year=_year(r.get("release_date")),
            poster_url=self.image_url(r.get("poster_path"), SIMILAR_POSTER_SIZE),
            rating=_rating(r.get("vote_average")),
        )
