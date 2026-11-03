"""DoesTheDogDie API v3 istemcisi.

Doğrulanmış uç noktalar (tümünde X-API-KEY header'ı):
  GET /items?imdb={imdb_id}            -> film kaydı (id)
  GET /items/{id}                      -> topicItemStats[]: topicId, topicName, yesSum,
                                          noSum, numComments
  GET /items/{id}/ratings?topicId={id} -> triggerDescription, cueDescription,
                                          position1/2/3 (saat/dakika/saniye)
  GET /topics                          -> konu listesi (ada göre filtrelenir)

Not: Yanıtların dış sarmalayıcısı (çıplak liste mi, {"items": [...]} mi) bu ortamdan
doğrulanamadı; ayrıştırıcı her iki şekli de kabul eder. Alan adları yukarıdaki
doğrulanmış listeyle sınırlıdır.

Kota: free tier dakikada 30 / ayda 5.000 istek. Film başına en fazla
2 + MAX_RATING_TOPICS istek yapılır, sonuç imdb_id bazında cache'lenir ve 429'da
Retry-After süresi boyunca DTDD hiç çağrılmaz (devre kesici).
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Iterable
from typing import Any

import httpx

from app.core.cache import CacheBackend
from app.core.errors import SourceNotFound, SourceUnavailable
from app.schemas.movie_response import CommunityTopic
from app.services.dtdd_topics import DISPLAY_ORDER, TOPIC_KEYS, match_topic_key

logger = logging.getLogger(__name__)

SOURCE = "dtdd"
MAX_RATING_TOPICS = 3
MAX_NOTES = 5
MAX_INLINE_RETRY_AFTER = 2.0
DEFAULT_COOLDOWN_SECONDS = 60.0
TOPICS_TTL_SECONDS = 24 * 3600
_WRAPPER_KEYS = ("items", "data", "results", "topics", "ratings", "item")


def _unwrap_list(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in _WRAPPER_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
            if isinstance(value, dict) and key == "item":
                return [value]
        if "id" in payload:
            return [payload]
    return []


def _find_key(payload: Any, key: str) -> Any:
    stack = [payload]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            if key in current:
                return current[key]
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return None


def _int(value: Any) -> int:
    try:
        return max(int(value), 0)
    except (TypeError, ValueError):
        return 0


def _format_position(item: dict[str, Any]) -> str | None:
    parts = [item.get("position1"), item.get("position2"), item.get("position3")]
    if all(p in (None, "") for p in parts):
        return None
    h, m, s = (_int(p) for p in parts)
    return f"{h:02d}:{m:02d}:{s:02d}"


class DTDDService:
    def __init__(
        self,
        client: httpx.AsyncClient,
        api_key: str,
        cache: CacheBackend,
        base_url: str = "https://www.doesthedogdie.com/api/v3",
        cache_ttl_seconds: int = 21600,
    ) -> None:
        self._client = client
        self._api_key = api_key
        self._cache = cache
        self._base_url = base_url.rstrip("/")
        self._cache_ttl = cache_ttl_seconds
        self._cooldown_until = 0.0
        self._topics_lock = asyncio.Lock()

    # ------------------------------------------------------------------ http
    def _check_cooldown(self) -> None:
        remaining = self._cooldown_until - time.monotonic()
        if remaining > 0:
            raise SourceUnavailable(SOURCE, f"rate_limited cooldown {remaining:.0f}s")

    def _start_cooldown(self, response: httpx.Response) -> float:
        retry_after = response.headers.get("Retry-After", "")
        try:
            seconds = float(retry_after)
        except ValueError:
            seconds = DEFAULT_COOLDOWN_SECONDS
        seconds = max(seconds, 1.0)
        self._cooldown_until = time.monotonic() + seconds
        return seconds

    @staticmethod
    def _error_code(response: httpx.Response) -> str:
        try:
            body = response.json()
        except ValueError:
            return ""
        if isinstance(body, dict):
            for key in ("error", "code", "message"):
                if isinstance(body.get(key), str):
                    return body[key]
        return ""

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        if not self._api_key:
            raise SourceUnavailable(SOURCE, "missing_api_key")
        self._check_cooldown()
        for attempt in range(2):
            try:
                response = await self._client.get(
                    f"{self._base_url}{path}",
                    params=params,
                    headers={"X-API-KEY": self._api_key, "Accept": "application/json"},
                )
            except httpx.TimeoutException as exc:
                raise SourceUnavailable(SOURCE, f"timeout {path}") from exc
            except httpx.HTTPError as exc:
                raise SourceUnavailable(SOURCE, f"transport {type(exc).__name__}") from exc

            status = response.status_code
            if status == 200:
                try:
                    return response.json()
                except ValueError as exc:
                    raise SourceUnavailable(SOURCE, "invalid_json") from exc
            if status == 404:
                raise SourceNotFound(SOURCE, "not_found")
            if status == 429:
                code = self._error_code(response) or "rate_limit_exceeded"
                wait = self._start_cooldown(response)
                # Kısa bekleme isteniyorsa ve ilk denemeyse bir kez uy; uzunsa pes et.
                if (
                    attempt == 0
                    and code != "monthly_limit_exceeded"
                    and wait <= MAX_INLINE_RETRY_AFTER
                ):
                    await asyncio.sleep(wait)
                    self._cooldown_until = 0.0
                    continue
                logger.warning("dtdd_rate_limited", extra={"code": code, "retry_after_s": wait})
                raise SourceUnavailable(SOURCE, code)
            if status in (401, 403):
                code = self._error_code(response) or (
                    "missing_api_key" if status == 401 else "upgrade_required"
                )
                logger.error("dtdd_auth_error", extra={"status": status, "code": code})
                raise SourceUnavailable(SOURCE, code)
            raise SourceUnavailable(SOURCE, f"http {status} {path}")
        raise SourceUnavailable(SOURCE, "rate_limit_exceeded")

    # ------------------------------------------------------------------ topics
    async def sensitive_topics(self) -> dict[int, str]:
        """topic_id -> topic_key. /topics'ten bir kez çekilir, 24 saat cache'lenir."""
        cached = await self._cache.get("dtdd:topics")
        if cached is not None:
            return {int(k): v for k, v in cached.items()}
        async with self._topics_lock:
            cached = await self._cache.get("dtdd:topics")
            if cached is not None:
                return {int(k): v for k, v in cached.items()}
            topics = _unwrap_list(await self._get("/topics"))
            mapping: dict[int, str] = {}
            for topic in topics:
                topic_id = topic.get("id", topic.get("topicId"))
                name = topic.get("name", topic.get("topicName"))
                key = match_topic_key(name if isinstance(name, str) else None)
                if key and topic_id is not None:
                    mapping[_int(topic_id)] = key
            missing = set(TOPIC_KEYS) - set(mapping.values())
            if missing:
                logger.warning("dtdd_topic_keys_unmatched", extra={"missing": sorted(missing)})
            logger.info("dtdd_topics_loaded", extra={"matched": len(mapping), "total": len(topics)})
            await self._cache.set(
                "dtdd:topics", {str(k): v for k, v in mapping.items()}, TOPICS_TTL_SECONDS
            )
            return mapping

    # ------------------------------------------------------------------ items
    async def _find_item_id(self, imdb_id: str) -> int:
        items = _unwrap_list(await self._get("/items", {"imdb": imdb_id}))
        if not items:
            raise SourceNotFound(SOURCE, "item_not_found")
        for item in items:
            item_imdb = item.get("imdbId") or item.get("imdb_id") or item.get("imdb")
            if item_imdb == imdb_id and item.get("id") is not None:
                return _int(item["id"])
        first = items[0].get("id")
        if first is None:
            raise SourceNotFound(SOURCE, "item_without_id")
        return _int(first)

    def _select_stats(
        self, stats: Iterable[dict[str, Any]], topic_map: dict[int, str]
    ) -> list[tuple[dict[str, Any], str]]:
        selected: list[tuple[dict[str, Any], str]] = []
        for stat in stats:
            topic_id = _int(stat.get("topicId"))
            key = topic_map.get(topic_id) or match_topic_key(stat.get("topicName"))
            if key:
                selected.append((stat, key))
        order = {key: i for i, key in enumerate(DISPLAY_ORDER)}
        selected.sort(key=lambda pair: (order.get(pair[1], 99), -_int(pair[0].get("yesSum"))))
        return selected

    async def _notes(self, item_id: int, topic_id: int) -> list[str]:
        try:
            ratings = _unwrap_list(
                await self._get(f"/items/{item_id}/ratings", {"topicId": topic_id})
            )
        except SourceNotFound:
            return []
        notes: list[str] = []
        for rating in ratings:
            text = rating.get("triggerDescription") or rating.get("cueDescription")
            if not isinstance(text, str) or not text.strip():
                continue
            position = _format_position(rating)
            note = f"{position} — {text.strip()}" if position else text.strip()
            if note not in notes:
                notes.append(note)
            if len(notes) == MAX_NOTES:
                break
        return notes

    async def get_community(self, imdb_id: str) -> list[CommunityTopic]:
        """Cinsellik/çıplaklık konularındaki topluluk oyları. Boş liste = film var, konu oyu yok."""
        cache_key = f"dtdd:item:{imdb_id}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return [CommunityTopic.model_validate(x) for x in cached]

        try:
            topic_map = await self.sensitive_topics()
        except SourceUnavailable:
            raise
        except SourceNotFound:
            topic_map = {}

        item_id = await self._find_item_id(imdb_id)
        detail = await self._get(f"/items/{item_id}")
        stats = _find_key(detail, "topicItemStats")
        stats = [s for s in stats if isinstance(s, dict)] if isinstance(stats, list) else []

        selected = self._select_stats(stats, topic_map)
        # Not çekimini, gerçekten "evet" oyu olan konularla sınırla (kota koruması).
        note_targets = [(stat, key) for stat, key in selected if _int(stat.get("yesSum")) > 0][
            :MAX_RATING_TOPICS
        ]
        notes_results = await asyncio.gather(
            *(self._notes(item_id, _int(stat.get("topicId"))) for stat, _ in note_targets),
            return_exceptions=True,
        )
        notes_by_topic: dict[int, list[str]] = {}
        for (stat, _), result in zip(note_targets, notes_results, strict=True):
            if isinstance(result, list):
                notes_by_topic[_int(stat.get("topicId"))] = result
            else:
                logger.info("dtdd_notes_failed", extra={"reason": str(result)})

        community: list[CommunityTopic] = []
        for stat, key in selected:
            yes, no = _int(stat.get("yesSum")), _int(stat.get("noSum"))
            topic_id = _int(stat.get("topicId"))
            community.append(
                CommunityTopic(
                    topic_id=topic_id,
                    topic_key=key,
                    question=str(stat.get("topicName") or key),
                    yes=yes,
                    no=no,
                    yes_ratio=round(yes / (yes + no), 3) if yes + no else 0.0,
                    comment_count=_int(stat.get("numComments")),
                    notes=notes_by_topic.get(topic_id, []),
                )
            )
        await self._cache.set(
            cache_key, [c.model_dump(mode="json") for c in community], self._cache_ttl
        )
        return community
