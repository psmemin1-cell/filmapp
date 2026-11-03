"""Dört kaynağı birleştiren agregasyon katmanı.

Aşama 1 (sıralı): TMDB arama + künye (imdb_id gerekli). Yalnızca bu aşama isteği
düşürebilir (MovieNotFound -> 404, SourceUnavailable -> 503).
Aşama 2 (paralel, asyncio.gather(return_exceptions=True)): yayın platformları,
parents guide, DTDD, benzer filmler. Her görev kalan toplam bütçeyle sınırlanır;
bütçe dolarsa eldekiyle dönülür ve düşen kaynak 'unavailable' işaretlenir.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from app.core.cache import CacheBackend
from app.core.errors import SourceError, SourceNotFound, SourceUnavailable
from app.core.text import normalize_title
from app.schemas.movie_response import (
    AdvisoryCategory,
    CommunityTopic,
    ContentAdvisory,
    Movie,
    MovieSearchResponse,
    SexNudity,
    SimilarMovie,
    Sources,
    SourceStatus,
    VoteBreakdown,
)
from app.services.dtdd_service import DTDDService
from app.services.movie_map_service import MovieMapService
from app.services.parents_guide.base import CATEGORY_ORDER, ParentsGuideProvider, ParentsGuideResult
from app.services.tmdb_service import SIMILAR_LIMIT, TMDBService

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass(slots=True)
class Outcome[T]:
    value: T | None
    status: SourceStatus
    duration_ms: int
    reason: str = ""


def status_for(exc: BaseException) -> SourceStatus:
    if isinstance(exc, SourceNotFound):
        return "not_found"
    return "unavailable"


class Aggregator:
    def __init__(
        self,
        tmdb: TMDBService,
        parents_guide: ParentsGuideProvider,
        dtdd: DTDDService,
        movie_map: MovieMapService,
        cache: CacheBackend,
        cache_ttl_seconds: int = 21600,
        degraded_cache_ttl_seconds: int = 300,
        total_budget_seconds: float = 12.0,
    ) -> None:
        self.tmdb = tmdb
        self.parents_guide = parents_guide
        self.dtdd = dtdd
        self.movie_map = movie_map
        self.cache = cache
        self.cache_ttl = cache_ttl_seconds
        self.degraded_cache_ttl = degraded_cache_ttl_seconds
        self.total_budget = total_budget_seconds
        self._inflight: dict[int, asyncio.Task[dict[str, Any]]] = {}

    # ================================================================== public
    async def search(self, raw_query: str) -> MovieSearchResponse:
        started = time.monotonic()
        query = normalize_title(raw_query)
        query_key = f"search:{query}"

        cached = await self.cache.get(query_key)
        if cached is not None:
            response = self._from_cache(cached, query)
            self._log(query, started, cached=True, response=response)
            return response

        deadline = started + self.total_budget
        # ---- Aşama 1: TMDB (istisnası isteği düşürür)
        hit = await self._with_deadline(self.tmdb.search(query), deadline)
        movie_key = f"movie:{hit.tmdb_id}"
        cached_movie = await self.cache.get(movie_key)
        if cached_movie is not None:
            await self.cache.set(query_key, cached_movie, self._ttl_for(cached_movie))
            response = self._from_cache(cached_movie, query)
            self._log(query, started, cached=True, response=response)
            return response

        # Aynı film için eşzamanlı istekleri tek bir hesaplamada birleştir (kota koruması).
        task = self._inflight.get(hit.tmdb_id)
        if task is None:
            task = asyncio.create_task(self._build(hit, deadline))
            self._inflight[hit.tmdb_id] = task
            task.add_done_callback(lambda _t, key=hit.tmdb_id: self._inflight.pop(key, None))
        payload = await asyncio.shield(task)

        ttl = self._ttl_for(payload)
        await self.cache.set(movie_key, payload, ttl)
        await self.cache.set(query_key, payload, ttl)
        response = self._from_cache(payload, query).model_copy(update={"cached": False})
        self._log(query, started, cached=False, response=response, timings=payload.get("_timings"))
        return response

    # ================================================================== build
    async def _build(self, hit: Any, deadline: float) -> dict[str, Any]:
        timings: dict[str, Any] = {}

        detail = await self._run("tmdb_details", lambda: self.tmdb.get_movie(hit), deadline)
        timings["tmdb_details"] = {"ms": detail.duration_ms, "status": detail.status}
        movie: Movie = detail.value or self.tmdb.movie_from_hit(hit)

        # ---- Aşama 2: kalan üç kaynak + yayın platformları paralel
        tasks: list[Awaitable[Outcome[Any]]] = [
            self._run("streaming", lambda: self.tmdb.get_watch_providers(movie.tmdb_id), deadline),
            self._run("imdb_parents_guide", lambda: self._parents_guide(movie.imdb_id), deadline),
            self._run("dtdd", lambda: self._dtdd(movie.imdb_id), deadline),
            self._run("similar", lambda: self._similar(movie), deadline),
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        streaming, guide, community, similar = (
            r if isinstance(r, Outcome) else Outcome(None, "unavailable", 0, repr(r))
            for r in results
        )
        for name, outcome in zip(
            ("streaming", "imdb_parents_guide", "dtdd", "similar"),
            (streaming, guide, community, similar),
            strict=True,
        ):
            timings[name] = {"ms": outcome.duration_ms, "status": outcome.status}
            if outcome.reason:
                timings[name]["reason"] = outcome.reason

        similar_value, similar_status = similar.value, similar.status
        if isinstance(similar_value, tuple):
            similar_value, similar_status = similar_value

        sources = Sources(
            tmdb="ok",
            imdb_parents_guide=guide.status,
            dtdd=community.status,
            similar=similar_status,
        )
        response = MovieSearchResponse(
            query="",
            movie=movie,
            streaming_tr=streaming.value if streaming.status == "ok" else None,
            content_advisory=self._content_advisory(guide.value, community.value),
            similar=similar_value if similar_status in ("ok", "fallback") else None,
            sources=sources,
        )
        payload = response.model_dump(mode="json")
        payload["_timings"] = timings
        return payload

    async def _parents_guide(self, imdb_id: str | None) -> ParentsGuideResult:
        if not imdb_id:
            raise SourceNotFound("imdb_parents_guide", "no_imdb_id")
        return await self.parents_guide.fetch(imdb_id)

    async def _dtdd(self, imdb_id: str | None) -> list[CommunityTopic]:
        if not imdb_id:
            raise SourceNotFound("dtdd", "no_imdb_id")
        return await self.dtdd.get_community(imdb_id)

    async def _similar(self, movie: Movie) -> tuple[list[SimilarMovie], SourceStatus]:
        primary_error: SourceError | None = None
        try:
            recs = await self.tmdb.get_recommendations(movie.tmdb_id)
        except SourceError as exc:
            recs, primary_error = [], exc
        if recs:
            return recs, "ok"

        if self.movie_map.enabled:
            try:
                titles = await self.movie_map.similar_titles(movie.title, limit=SIMILAR_LIMIT)
                resolved = await asyncio.gather(
                    *(self.tmdb.search_similar_candidate(t) for t in titles),
                    return_exceptions=True,
                )
                fallback = [
                    m
                    for m in resolved
                    if isinstance(m, SimilarMovie) and m.tmdb_id != movie.tmdb_id
                ][:SIMILAR_LIMIT]
                if fallback:
                    return fallback, "fallback"
            except SourceError as exc:
                logger.info("movie_map_failed", extra={"reason": str(exc)})

        if primary_error is not None:
            raise primary_error
        return [], "not_found"

    @staticmethod
    def _content_advisory(
        guide: ParentsGuideResult | None, community: list[CommunityTopic] | None
    ) -> ContentAdvisory | None:
        if guide is None and community is None:
            return None
        sex_nudity: SexNudity | None = None
        other: list[AdvisoryCategory] | None = None
        if guide is not None:
            nudity = guide.get("NUDITY")
            if nudity is not None:
                breakdown = nudity.breakdown
                sex_nudity = SexNudity(
                    severity=nudity.severity,
                    vote_total=nudity.vote_total,
                    vote_breakdown=VoteBreakdown(**breakdown) if breakdown else None,
                    descriptions=nudity.descriptions,
                )
            other = [
                AdvisoryCategory(name=cat.name, severity=cat.severity, vote_total=cat.vote_total)
                for cid in CATEGORY_ORDER
                if cid != "NUDITY" and (cat := guide.get(cid)) is not None
            ]
        return ContentAdvisory(sex_nudity=sex_nudity, other_categories=other, community=community)

    # ================================================================== helpers
    @staticmethod
    async def _with_deadline(coro: Awaitable[T], deadline: float) -> T:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise SourceUnavailable("tmdb", "budget_exhausted")
        try:
            return await asyncio.wait_for(coro, timeout=remaining)
        except TimeoutError as exc:
            raise SourceUnavailable("tmdb", "budget_exhausted") from exc

    async def _run(
        self, name: str, factory: Callable[[], Awaitable[T]], deadline: float
    ) -> Outcome[T]:
        """Bir kaynağı çalıştırır; hiçbir istisna dışarı sızmaz."""
        started = time.monotonic()
        remaining = deadline - started
        try:
            if remaining <= 0:
                raise SourceUnavailable(name, "budget_exhausted")
            value = await asyncio.wait_for(factory(), timeout=remaining)
            return Outcome(value, "ok", self._ms(started))
        except TimeoutError:
            return Outcome(None, "unavailable", self._ms(started), "budget_exhausted")
        except SourceError as exc:
            return Outcome(None, status_for(exc), self._ms(started), exc.reason)
        except Exception as exc:  # beklenmeyen hata da yalnızca o kaynağı düşürür
            logger.exception("source_crashed", extra={"source": name})
            return Outcome(None, "unavailable", self._ms(started), type(exc).__name__)

    @staticmethod
    def _ms(started: float) -> int:
        return int((time.monotonic() - started) * 1000)

    def _ttl_for(self, payload: dict[str, Any]) -> int:
        statuses = (payload.get("sources") or {}).values()
        timings = payload.get("_timings") or {}
        streaming_failed = (timings.get("streaming") or {}).get("status") == "unavailable"
        if "unavailable" in statuses or streaming_failed:
            return self.degraded_cache_ttl
        return self.cache_ttl

    @staticmethod
    def _from_cache(payload: dict[str, Any], query: str) -> MovieSearchResponse:
        data = {k: v for k, v in payload.items() if not k.startswith("_")}
        return MovieSearchResponse.model_validate({**data, "query": query, "cached": True})

    @staticmethod
    def _log(
        query: str,
        started: float,
        *,
        cached: bool,
        response: MovieSearchResponse,
        timings: dict[str, Any] | None = None,
    ) -> None:
        logger.info(
            "movie_search",
            extra={
                "query": query,
                "tmdb_id": response.movie.tmdb_id,
                "cached": cached,
                "total_ms": int((time.monotonic() - started) * 1000),
                "sources": response.sources.model_dump(),
                "timings": timings or {},
            },
        )
