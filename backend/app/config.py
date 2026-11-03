"""Uygulama yapılandırması: .env ve ortam değişkenlerinden okunur."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    tmdb_api_key: SecretStr = SecretStr("")
    dtdd_api_key: SecretStr = SecretStr("")
    enable_movie_map: bool = False

    # Parents guide sağlayıcısı: "scraper" (geliştirme) veya "dataset" (lisanslı veri seti)
    parents_guide_provider: Literal["scraper", "dataset"] = "scraper"
    parents_guide_dataset_path: str = ""

    cache_ttl_seconds: int = Field(default=21600, ge=0)
    degraded_cache_ttl_seconds: int = Field(default=300, ge=0)
    cache_max_entries: int = Field(default=2048, ge=1)

    log_level: str = "INFO"
    cors_allow_origins: str = "*"

    # Zaman bütçeleri (saniye)
    request_timeout_seconds: float = Field(default=6.0, gt=0)
    total_budget_seconds: float = Field(default=12.0, gt=0)

    # Dış servis taban adresleri (testlerde değiştirilebilir)
    tmdb_base_url: str = "https://api.themoviedb.org/3"
    tmdb_image_base_url: str = "https://image.tmdb.org/t/p"
    tmdb_web_base_url: str = "https://www.themoviedb.org"
    imdb_base_url: str = "https://www.imdb.com"
    dtdd_base_url: str = "https://www.doesthedogdie.com/api/v3"
    movie_map_base_url: str = "https://www.movie-map.com"

    @field_validator("log_level")
    @classmethod
    def _upper_log_level(cls, value: str) -> str:
        return value.upper()

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
