"""IMDb Parents Guide scraper (geliştirme amaçlı).

UYARI: IMDb Kullanım Koşulları veri madenciliğini yasaklar. Üretimde lisanslı
AWS Data Exchange veri seti ("IMDb Parents Guides: Severity Ratings & On-Screen
Descriptions") kullanılmalıdır -> `dataset.py`.

Birincil yol: <script id="__NEXT_DATA__"> JSON'u. Parents guide düğümünün yolu sürüm
sürüm değiştiği için sabit yol yazılmaz; props.pageProps altında özyinelemeli arama
yapılır ve kategori + oy sayısı/severity taşıyan düğümler toplanır.
İkincil yol: selectolax ile HTML fallback.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from typing import Any

import httpx
from selectolax.lexbor import LexborHTMLParser as HTMLParser

from app.core.errors import SourceNotFound, SourceUnavailable
from app.services.parents_guide.base import (
    VOTE_KEYS,
    CategoryResult,
    ParentsGuideResult,
    classify_category,
    normalize_severity,
)

logger = logging.getLogger(__name__)

SOURCE = "imdb_parents_guide"
MAX_DESCRIPTIONS = 15
BLOCKED_STATUSES = {401, 403, 405, 429}
BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
}

_LABEL_KEYS = ("category", "categoryId", "id", "title", "name", "text")
_VOTE_CONTAINER_KEYS = ("severityVotes", "votes", "voteCounts", "severityBreakdown", "breakdown")
_LEVEL_KEYS = ("voteType", "severityLevel", "level", "severity", "id", "text")
_COUNT_KEYS = ("votedFor", "voteCount", "votes", "count", "total")
_DESCRIPTION_CONTAINER_KEYS = ("guideItems", "items", "descriptions", "reviews")
_TEXT_KEYS = ("plaidHtml", "plainText", "markdown", "text", "value")
_WS_RE = re.compile(r"\s+")
_BREAK_RE = re.compile(r"<br\s*/?>|</p>|</li>|</div>", re.I)
_FOUND_THIS_RE = re.compile(
    r"([\d,]+)\s+of\s+([\d,]+)\s+found this\s+(none|mild|moderate|severe)", re.I
)
_SEVERITY_WORD_RE = re.compile(r"\b(None|Mild|Moderate|Severe)\b")


# =========================================================================== JSON yolu
def extract_next_data(html: str) -> dict[str, Any] | None:
    tree = HTMLParser(html)
    node = tree.css_first('script#__NEXT_DATA__[type="application/json"]') or tree.css_first(
        "script#__NEXT_DATA__"
    )
    if node is None:
        return None
    try:
        data = json.loads(node.text(strip=False) or "")
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _iter_dicts(obj: Any) -> Iterator[dict[str, Any]]:
    """Belge sırasını koruyarak (ön-sıra DFS) tüm sözlükleri dolaşır."""
    stack = [obj]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            yield current
            stack.extend(reversed(list(current.values())))
        elif isinstance(current, list):
            stack.extend(reversed(current))


def _label(node: dict[str, Any]) -> str | None:
    for key in _LABEL_KEYS:
        value = node.get(key)
        if isinstance(value, str) and classify_category(value):
            return value
        if isinstance(value, dict):
            for inner in ("id", "text", "name", "title"):
                if isinstance(value.get(inner), str) and classify_category(value[inner]):
                    return value[inner]
    return None


def _as_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.replace(",", "").isdigit():
        return int(value.replace(",", ""))
    return None


def _votes_from_flat(node: dict[str, Any]) -> dict[str, int]:
    """{'noneVotes': 3, 'mildVotes': 5, ...} şekli (IMDb veri sözlüğü)."""
    lowered = {k.lower(): v for k, v in node.items() if isinstance(k, str)}
    votes: dict[str, int] = {}
    for key in VOTE_KEYS:
        count = _as_int(lowered.get(f"{key}votes"))
        if count is not None:
            votes[key] = count
    return votes


def _votes_from_list(items: list[Any]) -> dict[str, int]:
    """[{'voteType': 'MILD', 'votedFor': 5}, ...] şekli."""
    votes: dict[str, int] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        level = next(
            (
                normalize_severity(item.get(k))
                for k in _LEVEL_KEYS
                if normalize_severity(item.get(k))
            ),
            None,
        )
        count = next(
            (_as_int(item.get(k)) for k in _COUNT_KEYS if _as_int(item.get(k)) is not None), None
        )
        if level and count is not None:
            votes[level.lower()] = votes.get(level.lower(), 0) + count
    return votes


def _extract_votes(node: dict[str, Any]) -> dict[str, int]:
    votes = _votes_from_flat(node)
    if votes:
        return votes
    for key in _VOTE_CONTAINER_KEYS:
        container = node.get(key)
        if isinstance(container, dict):
            votes = _votes_from_flat(container)
        elif isinstance(container, list):
            votes = _votes_from_list(container)
        if votes:
            return votes
    return {}


def _extract_reported_severity(node: dict[str, Any]) -> Any:
    for key in ("severity", "severitySummary", "rating"):
        value = node.get(key)
        if isinstance(value, dict):
            for inner in ("text", "id", "value"):
                level = normalize_severity(value.get(inner))
                if level:
                    return level
        level = normalize_severity(value)
        if level:
            return level
    return None


def strip_html(value: str) -> str:
    if "<" in value:
        # Satır içi etiketler (<b>, <i>) kelimeyi bölmesin; blok/satır sonları boşluk olsun.
        value = _BREAK_RE.sub(" ", value)
        value = HTMLParser(f"<div>{value}</div>").text(separator="")
    text = value
    return _WS_RE.sub(" ", text).strip()


def _extract_descriptions(node: dict[str, Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(raw: Any) -> None:
        if isinstance(raw, str):
            text = strip_html(raw)
            if text and text not in seen:
                seen.add(text)
                out.append(text)

    for key in _DESCRIPTION_CONTAINER_KEYS:
        container = node.get(key)
        if container is None:
            continue
        if isinstance(container, list) and all(isinstance(x, str) for x in container):
            for item in container:
                add(item)
            continue
        for item in _iter_dicts(container):
            text = item.get("text")
            if isinstance(text, str):
                add(text)
            elif isinstance(text, dict):
                for tk in _TEXT_KEYS:
                    if isinstance(text.get(tk), str):
                        add(text[tk])
                        break
    return out[:MAX_DESCRIPTIONS]


def extract_categories(payload: Any) -> dict[str, CategoryResult]:
    """Herhangi bir JSON ağacında parents guide kategorilerini özyinelemeli bulur.

    Bir düğüm kategori sayılmak için tanınan bir kategori etiketi VE oy sayısı veya
    severity taşımalıdır (yalnızca etiket yetmez: "Sex Education" gibi bir film adı
    yanlış pozitif üretmesin). Aynı kategori birden çok kez bulunursa en çok oya
    sahip olan tutulur, açıklamalar birleştirilir.
    """
    found: dict[str, CategoryResult] = {}
    for node in _iter_dicts(payload):
        label = _label(node)
        category_id = classify_category(label)
        if not category_id:
            continue
        votes = _extract_votes(node)
        reported = _extract_reported_severity(node)
        if not votes and not reported:
            continue
        candidate = CategoryResult(
            category_id=category_id,
            votes=votes,
            reported_severity=reported,
            descriptions=_extract_descriptions(node),
        )
        existing = found.get(category_id)
        if existing is None or candidate.vote_total > existing.vote_total:
            if existing and not candidate.descriptions:
                candidate.descriptions = existing.descriptions
            found[category_id] = candidate
        elif not existing.descriptions and candidate.descriptions:
            existing.descriptions = candidate.descriptions
    return found


def parse_next_data(data: dict[str, Any]) -> dict[str, CategoryResult]:
    page_props = (data.get("props") or {}).get("pageProps")
    return extract_categories(page_props if page_props is not None else data)


# =========================================================================== HTML fallback
def parse_html_fallback(html: str) -> dict[str, CategoryResult]:
    tree = HTMLParser(html)
    found: dict[str, CategoryResult] = {}
    for section in tree.css("section[id], div[id], section[data-testid], div[data-testid]"):
        ident = section.attributes.get("id") or section.attributes.get("data-testid") or ""
        category_id = classify_category(ident)
        if not category_id or category_id in found:
            continue
        text = _WS_RE.sub(" ", section.text(separator=" "))
        result = CategoryResult(category_id=category_id)
        match = _FOUND_THIS_RE.search(text)
        if match:
            result.reported_total = int(match.group(2).replace(",", ""))
            result.reported_severity = normalize_severity(match.group(3))
        else:
            pill = section.css_first("[class*=pill], [class*=severity]")
            word = _SEVERITY_WORD_RE.search(pill.text() if pill else "")
            result.reported_severity = normalize_severity(word.group(1)) if word else None
        for li in section.css("li"):
            item = _WS_RE.sub(" ", li.text(separator=" ")).strip()
            if (
                len(item) > 15
                and not _FOUND_THIS_RE.search(item)
                and item not in result.descriptions
            ):
                result.descriptions.append(item)
        result.descriptions = result.descriptions[:MAX_DESCRIPTIONS]
        if result.reported_severity or result.descriptions:
            found[category_id] = result
    return found


def looks_like_challenge(response: httpx.Response) -> bool:
    if "x-amzn-waf-action" in {k.lower() for k in response.headers}:
        return True
    body = response.text[:4000].lower()
    return "awswafintegration" in body or "challenge.js" in body or "captcha" in body


# =========================================================================== provider
class ImdbScraperProvider:
    name = "imdb_scraper"

    def __init__(self, client: httpx.AsyncClient, base_url: str = "https://www.imdb.com") -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    async def _fetch_page(self, url: str) -> httpx.Response:
        """En fazla 1 retry (yalnızca timeout/bağlantı/5xx için). 403/429'da retry yok."""
        last_exc: Exception | None = None
        for attempt in range(2):
            try:
                response = await self._client.get(url, headers=BROWSER_HEADERS)
            except httpx.TimeoutException as exc:
                last_exc = SourceUnavailable(SOURCE, "timeout")
                last_exc.__cause__ = exc
            except httpx.HTTPError as exc:
                last_exc = SourceUnavailable(SOURCE, f"transport {type(exc).__name__}")
                last_exc.__cause__ = exc
            else:
                if response.status_code >= 500 and attempt == 0:
                    last_exc = SourceUnavailable(SOURCE, f"http {response.status_code}")
                    continue
                return response
        assert last_exc is not None
        raise last_exc

    async def fetch(self, imdb_id: str) -> ParentsGuideResult:
        if not re.fullmatch(r"tt\d{5,10}", imdb_id or ""):
            raise SourceNotFound(SOURCE, "invalid_imdb_id")
        response = await self._fetch_page(f"{self._base_url}/title/{imdb_id}/parentalguide/")

        if response.status_code == 404:
            raise SourceNotFound(SOURCE, "http 404")
        if response.status_code in BLOCKED_STATUSES:
            raise SourceUnavailable(SOURCE, f"blocked http {response.status_code}")
        if response.status_code != 200:
            raise SourceUnavailable(SOURCE, f"http {response.status_code}")

        html = response.text
        next_data = extract_next_data(html)
        if next_data is not None:
            categories = parse_next_data(next_data)
            if not categories:
                logger.warning(
                    "parents_guide_node_missing", extra={"imdb_id": imdb_id, "path": "next_data"}
                )
                categories = parse_html_fallback(html)
                if not categories:
                    raise SourceNotFound(SOURCE, "no_parents_guide_data")
            return ParentsGuideResult(imdb_id=imdb_id, categories=categories)

        if looks_like_challenge(response):
            raise SourceUnavailable(SOURCE, "waf_challenge")
        categories = parse_html_fallback(html)
        if not categories:
            raise SourceUnavailable(SOURCE, "next_data_missing")
        logger.info("parents_guide_html_fallback", extra={"imdb_id": imdb_id})
        return ParentsGuideResult(imdb_id=imdb_id, categories=categories)
