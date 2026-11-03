from __future__ import annotations

import json

import httpx
import pytest
import respx

from app.core.errors import SourceNotFound, SourceUnavailable
from app.services.parents_guide.base import (
    CategoryResult,
    ParentsGuideProvider,
    median_severity,
    vote_breakdown,
)
from app.services.parents_guide.dataset import DatasetParentsGuideProvider, JsonlDatasetLookup
from app.services.parents_guide.scraper import (
    ImdbScraperProvider,
    extract_next_data,
    parse_html_fallback,
    parse_next_data,
)
from tests.conftest import IMDB, load_text

URL = f"{IMDB}/title/tt15398776/parentalguide/"


@pytest.fixture
def scraper(client: httpx.AsyncClient) -> ImdbScraperProvider:
    return ImdbScraperProvider(client)


# ----------------------------------------------------------------- saf hesaplamalar
def test_median_not_mean() -> None:
    # Ortalama "Moderate"e yakın olurdu; medyan "None".
    assert median_severity({"none": 6, "mild": 0, "moderate": 0, "severe": 5}) == "None"
    assert median_severity({"none": 49, "mild": 87, "moderate": 181, "severe": 95}) == "Moderate"
    assert median_severity({"none": 0, "mild": 0, "moderate": 0, "severe": 1}) == "Severe"
    assert median_severity({}) is None


def test_vote_breakdown_sums_to_one() -> None:
    ratios = vote_breakdown({"none": 1, "mild": 1, "moderate": 1, "severe": 0})
    assert ratios is not None
    assert abs(sum(ratios.values()) - 1.0) <= 0.01
    assert all(0.0 <= v <= 1.0 for v in ratios.values())
    assert vote_breakdown({"none": 0}) is None


def test_reported_severity_used_without_votes() -> None:
    result = CategoryResult(category_id="NUDITY", reported_severity="Mild", reported_total=10)
    assert result.severity == "Mild"
    assert result.vote_total == 10
    assert result.breakdown is None


# ----------------------------------------------------------------- __NEXT_DATA__ parser
def test_parse_recorded_fixture_flat_shape() -> None:
    data = extract_next_data(load_text("imdb_parentalguide_tt15398776.html"))
    assert data is not None
    categories = parse_next_data(data)
    assert set(categories) == {"NUDITY", "VIOLENCE", "PROFANITY", "ALCOHOL", "FRIGHTENING"}
    nudity = categories["NUDITY"]
    assert nudity.vote_total == 412
    assert nudity.severity == "Moderate"
    assert nudity.breakdown == {"none": 0.119, "mild": 0.211, "moderate": 0.439, "severe": 0.231}
    assert nudity.descriptions[0] == "A couple has sex twice; a woman's breasts are shown."
    assert "<b>" not in " ".join(nudity.descriptions)
    assert categories["VIOLENCE"].severity == "Mild"


def test_parse_graphql_shape_without_fixed_path() -> None:
    data = extract_next_data(load_text("imdb_parentalguide_graphql_shape.html"))
    assert data is not None
    categories = parse_next_data(data)
    assert set(categories) == {
        "NUDITY",
        "VIOLENCE",
    }  # film adı "Sex Education" yanlış pozitif değil
    assert categories["NUDITY"].votes == {"none": 10, "mild": 20, "moderate": 50, "severe": 20}
    assert categories["NUDITY"].severity == "Moderate"
    assert categories["NUDITY"].descriptions == ["Brief nudity."]
    assert categories["VIOLENCE"].severity == "None"


def test_next_data_missing_returns_none() -> None:
    assert extract_next_data("<html><body>nothing</body></html>") is None
    assert extract_next_data('<script id="__NEXT_DATA__">{not json</script>') is None


def test_html_fallback_legacy_layout() -> None:
    categories = parse_html_fallback(load_text("imdb_parentalguide_legacy.html"))
    nudity = categories["NUDITY"]
    assert nudity.severity == "Moderate"
    assert nudity.vote_total == 412
    assert nudity.breakdown is None
    assert nudity.descriptions == ["A couple has sex twice; a woman's breasts are shown."]
    assert categories["VIOLENCE"].severity == "Mild"


# ----------------------------------------------------------------- provider (HTTP)
async def test_fetch_success(router: respx.MockRouter, scraper: ImdbScraperProvider) -> None:
    router.get(URL).respond(text=load_text("imdb_parentalguide_tt15398776.html"))
    assert isinstance(scraper, ParentsGuideProvider)
    result = await scraper.fetch("tt15398776")
    assert result.get("NUDITY") is not None


async def test_fetch_404_is_not_found(
    router: respx.MockRouter, scraper: ImdbScraperProvider
) -> None:
    router.get(URL).respond(status_code=404)
    with pytest.raises(SourceNotFound):
        await scraper.fetch("tt15398776")


@pytest.mark.parametrize("status", [403, 429])
async def test_blocked_gives_up_without_retry(
    router: respx.MockRouter, scraper: ImdbScraperProvider, status: int
) -> None:
    route = router.get(URL).respond(status_code=status)
    with pytest.raises(SourceUnavailable):
        await scraper.fetch("tt15398776")
    assert route.call_count == 1


async def test_waf_challenge_is_unavailable(
    router: respx.MockRouter, scraper: ImdbScraperProvider
) -> None:
    router.get(URL).respond(
        status_code=200,
        text=load_text("imdb_waf_challenge.html"),
        headers={"x-amzn-waf-action": "challenge"},
    )
    with pytest.raises(SourceUnavailable):
        await scraper.fetch("tt15398776")


async def test_timeout_retries_once_then_gives_up(
    router: respx.MockRouter, scraper: ImdbScraperProvider
) -> None:
    route = router.get(URL).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(SourceUnavailable):
        await scraper.fetch("tt15398776")
    assert route.call_count == 2  # ilk deneme + en fazla 1 retry


async def test_5xx_then_success(router: respx.MockRouter, scraper: ImdbScraperProvider) -> None:
    route = router.get(URL).mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, text=load_text("imdb_parentalguide_tt15398776.html")),
        ]
    )
    result = await scraper.fetch("tt15398776")
    assert route.call_count == 2
    assert result.get("NUDITY") is not None


async def test_empty_guide_is_not_found(
    router: respx.MockRouter, scraper: ImdbScraperProvider
) -> None:
    router.get(URL).respond(text=load_text("imdb_parentalguide_empty.html"))
    with pytest.raises(SourceNotFound):
        await scraper.fetch("tt15398776")


async def test_invalid_imdb_id(scraper: ImdbScraperProvider) -> None:
    with pytest.raises(SourceNotFound):
        await scraper.fetch("not-an-id")


# ----------------------------------------------------------------- dataset provider
async def test_dataset_provider_same_shape(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "guide.jsonl"
    row = {
        "imdb_id": "tt15398776",
        "categories": [
            {
                "category": "NUDITY",
                "severity": "Moderate",
                "noneVotes": 49,
                "mildVotes": 87,
                "moderateVotes": 181,
                "severeVotes": 95,
                "descriptions": ["On-screen description."],
            }
        ],
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")
    provider = DatasetParentsGuideProvider(JsonlDatasetLookup(path))
    assert isinstance(provider, ParentsGuideProvider)
    result = await provider.fetch("tt15398776")
    nudity = result.get("NUDITY")
    assert nudity is not None and nudity.vote_total == 412
    assert nudity.descriptions == ["On-screen description."]
    with pytest.raises(SourceNotFound):
        await provider.fetch("tt0000001")


async def test_dataset_not_configured() -> None:
    with pytest.raises(SourceUnavailable):
        await DatasetParentsGuideProvider(None).fetch("tt15398776")
