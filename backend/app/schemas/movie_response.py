"""GET /api/v1/movies/search yanıt sözleşmesi.

Bu modeller README'deki JSON sözleşmesinin birebir karşılığıdır; Android tarafındaki
@Serializable DTO'lar da buradan türetilir. Alan adlarını değiştirmeyin.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, model_validator

Severity = Literal["None", "Mild", "Moderate", "Severe"]
SourceStatus = Literal["ok", "unavailable", "not_found", "fallback"]

SEVERITY_LEVELS: tuple[Severity, ...] = ("None", "Mild", "Moderate", "Severe")
DTDD_ATTRIBUTION = "Powered by DoesTheDogDie.com"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class Movie(_Model):
    tmdb_id: int
    imdb_id: str | None = None
    title: str
    original_title: str | None = None
    year: int | None = None
    runtime_minutes: int | None = None
    overview: str = ""
    poster_url: str | None = None
    rating: float | None = None
    rating_source: Literal["tmdb"] = "tmdb"
    rating_votes: int | None = None


class Provider(_Model):
    name: str
    logo_url: str | None = None


class StreamingTR(_Model):
    available: bool
    flatrate: list[Provider] = Field(default_factory=list)
    rent: list[Provider] = Field(default_factory=list)
    buy: list[Provider] = Field(default_factory=list)
    tmdb_link: str


class VoteBreakdown(_Model):
    none: float = Field(ge=0.0, le=1.0)
    mild: float = Field(ge=0.0, le=1.0)
    moderate: float = Field(ge=0.0, le=1.0)
    severe: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _sums_to_one(self) -> VoteBreakdown:
        total = self.none + self.mild + self.moderate + self.severe
        if abs(total - 1.0) > 0.01:
            raise ValueError(f"vote_breakdown toplamı 1.0 ± 0.01 olmalı, {total:.4f} geldi")
        return self


class SexNudity(_Model):
    severity: Severity | None = None
    vote_total: int = Field(default=0, ge=0)
    vote_breakdown: VoteBreakdown | None = None
    descriptions: list[str] = Field(default_factory=list)


class AdvisoryCategory(_Model):
    name: str
    severity: Severity | None = None
    vote_total: int = Field(default=0, ge=0)


class CommunityTopic(_Model):
    topic_id: int
    # Sözleşmeye eklenen alan: Android'in soruyu strings.xml ile Türkçeleştirmesi için
    # kararlı anahtar ("nudity", "sex_scene", "sexual_assault"). DTDD topic ID'leri
    # sabit olmadığından ID yerine bu anahtar kullanılır.
    topic_key: str | None = None
    question: str
    yes: int = Field(ge=0)
    no: int = Field(ge=0)
    yes_ratio: float = Field(ge=0.0, le=1.0)
    comment_count: int = Field(default=0, ge=0)
    notes: list[str] = Field(default_factory=list)


class ContentAdvisory(_Model):
    sex_nudity: SexNudity | None = None
    other_categories: list[AdvisoryCategory] | None = None
    community: list[CommunityTopic] | None = None
    attribution: str = DTDD_ATTRIBUTION


class SimilarMovie(_Model):
    tmdb_id: int
    title: str
    year: int | None = None
    poster_url: str | None = None
    rating: float | None = None


class Sources(_Model):
    tmdb: SourceStatus
    imdb_parents_guide: SourceStatus
    dtdd: SourceStatus
    similar: SourceStatus


class MovieSearchResponse(_Model):
    query: str
    movie: Movie
    streaming_tr: StreamingTR | None = None
    content_advisory: ContentAdvisory | None = None
    similar: list[SimilarMovie] | None = None
    sources: Sources
    cached: bool = False
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_serializer("generated_at")
    def _serialize_generated_at(self, value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class MovieNotFoundBody(_Model):
    detail: Literal["movie_not_found"] = "movie_not_found"
    query: str


class UpstreamUnavailableBody(_Model):
    detail: Literal["upstream_unavailable"] = "upstream_unavailable"
    source: Literal["tmdb"] = "tmdb"
    query: str
