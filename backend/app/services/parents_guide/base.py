"""Parents guide sağlayıcı arayüzü ve ortak hesaplama yardımcıları.

Scraper (geliştirme) ile lisanslı AWS Data Exchange veri seti (üretim) aynı protokolü
uygular; aggregator yalnızca `ParentsGuideProvider`'ı bilir.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.schemas.movie_response import SEVERITY_LEVELS, Severity

VOTE_KEYS: tuple[str, ...] = ("none", "mild", "moderate", "severe")

# IMDb kategori kimlikleri -> sözleşmedeki görünen adlar.
CATEGORY_NAMES: dict[str, str] = {
    "NUDITY": "Sex & Nudity",
    "VIOLENCE": "Violence & Gore",
    "PROFANITY": "Profanity",
    "ALCOHOL": "Alcohol, Drugs & Smoking",
    "FRIGHTENING": "Frightening & Intense Scenes",
}
CATEGORY_ORDER: tuple[str, ...] = tuple(CATEGORY_NAMES)

_CATEGORY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("NUDITY", re.compile(r"nudity|sex", re.I)),
    ("VIOLENCE", re.compile(r"violence|gore", re.I)),
    ("PROFANITY", re.compile(r"profanity|language", re.I)),
    ("ALCOHOL", re.compile(r"alcohol|drug|smok", re.I)),
    ("FRIGHTENING", re.compile(r"frighten|intense", re.I)),
)


def classify_category(label: str | None) -> str | None:
    """'NUDITY', 'Sex & Nudity', 'advisory-nudity' gibi etiketleri kanonik kimliğe çevirir."""
    if not label:
        return None
    for key, pattern in _CATEGORY_PATTERNS:
        if pattern.search(label):
            return key
    return None


def normalize_severity(value: object) -> Severity | None:
    """'Mild', 'MILD', 'mildVotes', 'severityMild' -> 'Mild'. Tanınmazsa None."""
    if not isinstance(value, str):
        return None
    lowered = value.lower()
    # 'moderate' 'none' içermez; ama 'none' kontrolünü en sona bırakmak 'nonevotes'
    # dışındaki yanlış eşleşmeleri önler.
    for level in ("severe", "moderate", "mild", "none"):
        if level in lowered:
            return level.capitalize()  # type: ignore[return-value]
    return None


@dataclass(slots=True)
class CategoryResult:
    category_id: str
    votes: dict[str, int] = field(default_factory=dict)
    reported_severity: Severity | None = None
    # Yalnızca toplam oy bilinen durumlar için (ör. HTML fallback: "34 of 50 found this mild").
    reported_total: int = 0
    descriptions: list[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return CATEGORY_NAMES[self.category_id]

    @property
    def vote_total(self) -> int:
        summed = sum(max(self.votes.get(k, 0), 0) for k in VOTE_KEYS)
        return summed or max(self.reported_total, 0)

    @property
    def severity(self) -> Severity | None:
        """Oy varsa medyan; yoksa kaynağın bildirdiği seviye."""
        return median_severity(self.votes) or self.reported_severity

    @property
    def breakdown(self) -> dict[str, float] | None:
        return vote_breakdown(self.votes)


@dataclass(slots=True)
class ParentsGuideResult:
    imdb_id: str
    categories: dict[str, CategoryResult] = field(default_factory=dict)

    def get(self, category_id: str) -> CategoryResult | None:
        return self.categories.get(category_id)


def median_severity(votes: dict[str, int]) -> Severity | None:
    """Sıralı oy dağılımının medyanı (ortalaması değil).

    Çift toplamda alt medyan alınır: toplamın yarısına (yukarı yuvarlanmış) ulaşan
    ilk seviye.
    """
    total = sum(max(votes.get(k, 0), 0) for k in VOTE_KEYS)
    if total <= 0:
        return None
    threshold = (total + 1) // 2
    cumulative = 0
    for key, level in zip(VOTE_KEYS, SEVERITY_LEVELS, strict=True):
        cumulative += max(votes.get(key, 0), 0)
        if cumulative >= threshold:
            return level
    return None


def vote_breakdown(votes: dict[str, int]) -> dict[str, float] | None:
    """0–1 arası oranlar; yuvarlama artığı en büyük paya eklenir, toplam tam 1.0 olur."""
    total = sum(max(votes.get(k, 0), 0) for k in VOTE_KEYS)
    if total <= 0:
        return None
    ratios = {k: round(max(votes.get(k, 0), 0) / total, 3) for k in VOTE_KEYS}
    drift = round(1.0 - sum(ratios.values()), 3)
    if drift:
        largest = max(ratios, key=lambda k: ratios[k])
        ratios[largest] = round(ratios[largest] + drift, 3)
    return ratios


@runtime_checkable
class ParentsGuideProvider(Protocol):
    """imdb_id -> ParentsGuideResult.

    Hata sözleşmesi: sağlayıcıya ulaşılamazsa SourceUnavailable, başlık için veri
    yoksa SourceNotFound yükseltir. Başka istisna sızdırmaz.
    """

    name: str

    async def fetch(self, imdb_id: str) -> ParentsGuideResult: ...
