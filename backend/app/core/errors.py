"""Uygulama genelinde kullanılan istisnalar."""

from __future__ import annotations


class SourceError(Exception):
    """Bir dış kaynağa ait hataların ortak tabanı."""

    def __init__(self, source: str, reason: str = "") -> None:
        self.source = source
        self.reason = reason
        super().__init__(f"{source}: {reason}" if reason else source)


class SourceUnavailable(SourceError):
    """Dış servis hatası, timeout, rate limit veya erişim engeli (sources -> 'unavailable')."""


class SourceNotFound(SourceError):
    """Kaynak filmi tanımıyor (sources -> 'not_found')."""


class MovieNotFound(Exception):
    """TMDB aramasında film bulunamadı (HTTP 404)."""

    def __init__(self, query: str) -> None:
        self.query = query
        super().__init__(f"movie_not_found: {query}")
