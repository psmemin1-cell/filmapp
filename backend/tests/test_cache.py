from __future__ import annotations

from app.core.cache import CacheBackend, InMemoryTTLCache
from app.core.text import fold_title, normalize_title


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


async def test_ttl_expiry() -> None:
    clock = FakeClock()
    cache = InMemoryTTLCache(timer=clock)
    assert isinstance(cache, CacheBackend)
    await cache.set("a", {"x": 1}, ttl_seconds=60)
    await cache.set("b", {"y": 2}, ttl_seconds=3600)
    assert await cache.get("a") == {"x": 1}
    clock.now += 61
    assert await cache.get("a") is None
    assert await cache.get("b") == {"y": 2}


async def test_zero_ttl_not_stored() -> None:
    cache = InMemoryTTLCache()
    await cache.set("a", 1, ttl_seconds=0)
    assert await cache.get("a") is None


async def test_delete_and_clear() -> None:
    cache = InMemoryTTLCache()
    await cache.set("a", 1, 10)
    await cache.set("b", 2, 10)
    await cache.delete("a")
    assert await cache.get("a") is None
    await cache.clear()
    assert len(cache) == 0


def test_normalize_keeps_turkish_chars() -> None:
    assert normalize_title("  Yüzüklerin   Efendisi ") == "yüzüklerin efendisi"
    assert normalize_title("KIŞ UYKUSU") == "kiş uykusu"
    assert normalize_title("İstanbul") == "istanbul"
    assert normalize_title("Oppenheimer") == normalize_title("OPPENHEIMER")


def test_fold_for_comparison() -> None:
    assert fold_title("Kış Uykusu") == "kis uykusu"
    assert fold_title("Yüzüklerin Efendisi: Kralın Dönüşü") == "yuzuklerin efendisi kralin donusu"
