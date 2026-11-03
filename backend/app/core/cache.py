"""TTL cache katmanı.

`CacheBackend` protokolü async olduğu için Redis gibi ağ tabanlı bir backend'e
çağıran kodu değiştirmeden geçilebilir. Başlangıç implementasyonu cachetools.TLRUCache
ile kayıt başına TTL destekler (tam yanıt 6 saat, kısmi bozuk yanıt daha kısa).
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from cachetools import TLRUCache


@runtime_checkable
class CacheBackend(Protocol):
    async def get(self, key: str) -> Any | None: ...

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None: ...

    async def delete(self, key: str) -> None: ...

    async def clear(self) -> None: ...


def _ttu(_key: str, value: tuple[int, Any], now: float) -> float:
    ttl, _ = value
    return now + ttl


class InMemoryTTLCache:
    """Süreç içi cache. Tek event loop'ta çalıştığı için kilit gerektirmez."""

    def __init__(self, maxsize: int = 2048, timer: Callable[[], float] = time.monotonic) -> None:
        self._cache: TLRUCache[str, tuple[int, Any]] = TLRUCache(
            maxsize=maxsize, ttu=_ttu, timer=timer
        )

    async def get(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        return None if entry is None else entry[1]

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        if ttl_seconds <= 0:
            return
        self._cache[key] = (ttl_seconds, value)

    async def delete(self, key: str) -> None:
        self._cache.pop(key, None)

    async def clear(self) -> None:
        self._cache.clear()

    def __len__(self) -> int:
        return len(self._cache)
