"""Paylaşılan httpx.AsyncClient.

Client uygulama lifespan'inde bir kez oluşturulur ve tüm servislere enjekte edilir;
servisler kendi client'ını açmaz (bağlantı havuzu ve TLS oturumları paylaşılır).
"""

from __future__ import annotations

import httpx

DEFAULT_USER_AGENT = "CineScope/1.0 (+https://github.com/psmemin1-cell/filmapp)"


def create_http_client(timeout_seconds: float) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout_seconds),
        limits=httpx.Limits(max_connections=100, max_keepalive_connections=20),
        follow_redirects=True,
        headers={"User-Agent": DEFAULT_USER_AGENT, "Accept": "application/json"},
    )
