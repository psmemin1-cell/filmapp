from __future__ import annotations

import httpx
import pytest
import respx

from app.core.cache import InMemoryTTLCache
from app.core.errors import SourceNotFound, SourceUnavailable
from app.services.dtdd_service import DTDDService
from app.services.dtdd_topics import match_topic_key
from tests.conftest import DTDD, load_json, mock_dtdd_happy


@pytest.fixture
def dtdd(client: httpx.AsyncClient, cache: InMemoryTTLCache) -> DTDDService:
    return DTDDService(client, api_key="test-dtdd-key", cache=cache)


@pytest.mark.parametrize(
    ("name", "key"),
    [
        ("Is there nudity?", "nudity"),
        ("Is there a sex scene?", "sex_scene"),
        ("Is someone sexually assaulted?", "sexual_assault"),
        ("Is there a sexual assault scene?", "sexual_assault"),
        ("Does the dog die?", None),
        ("Is there gun violence?", None),
    ],
)
def test_topic_matching_by_name(name: str, key: str | None) -> None:
    assert match_topic_key(name) == key


async def test_success(router: respx.MockRouter, dtdd: DTDDService) -> None:
    mock_dtdd_happy(router)
    community = await dtdd.get_community("tt15398776")

    assert [c.topic_key for c in community] == ["nudity", "sex_scene", "sexual_assault"]
    nudity = next(c for c in community if c.topic_key == "nudity")
    assert nudity.topic_id == 108
    assert nudity.question == "Is there nudity?"
    assert (nudity.yes, nudity.no, nudity.comment_count) == (184, 31, 12)
    assert nudity.yes_ratio == 0.856  # 184 / (184 + 31)
    assert nudity.notes[0] == (
        "00:32:10 — Florence Pugh appears topless during a scene with Oppenheimer."
    )
    sex_scene = next(c for c in community if c.topic_key == "sex_scene")
    assert sex_scene.notes == ["00:31:00 — After they talk in the library."]

    # Tüm isteklerde X-API-KEY header'ı
    for call in router.calls:
        assert call.request.headers["X-API-KEY"] == "test-dtdd-key"


async def test_result_is_cached_per_imdb_id(router: respx.MockRouter, dtdd: DTDDService) -> None:
    mock_dtdd_happy(router)
    await dtdd.get_community("tt15398776")
    calls = len(router.calls)
    await dtdd.get_community("tt15398776")
    assert len(router.calls) == calls  # ikinci çağrı ağa çıkmaz


async def test_topics_loaded_once(router: respx.MockRouter, dtdd: DTDDService) -> None:
    route = router.get(f"{DTDD}/topics").respond(json=load_json("dtdd_topics.json"))
    first = await dtdd.sensitive_topics()
    second = await dtdd.sensitive_topics()
    assert (
        first
        == second
        == {153: "sex_scene", 108: "nudity", 172: "sexual_assault", 175: "sexual_assault"}
    )
    assert route.call_count == 1


async def test_bare_list_payloads_accepted(router: respx.MockRouter, dtdd: DTDDService) -> None:
    router.get(f"{DTDD}/topics").respond(json=load_json("dtdd_topics.json")["topics"])
    router.get(f"{DTDD}/items").respond(json=load_json("dtdd_items_by_imdb.json")["items"])
    detail = load_json("dtdd_item_detail.json")
    router.get(f"{DTDD}/items/1013637").respond(json=detail)
    router.get(f"{DTDD}/items/1013637/ratings").respond(json=[])
    community = await dtdd.get_community("tt15398776")
    assert {c.topic_id for c in community} == {108, 153, 175}


async def test_item_not_found_empty_list(router: respx.MockRouter, dtdd: DTDDService) -> None:
    router.get(f"{DTDD}/topics").respond(json=load_json("dtdd_topics.json"))
    router.get(f"{DTDD}/items").respond(json=load_json("dtdd_items_empty.json"))
    with pytest.raises(SourceNotFound):
        await dtdd.get_community("tt0000001")


async def test_item_404(router: respx.MockRouter, dtdd: DTDDService) -> None:
    router.get(f"{DTDD}/topics").respond(json=load_json("dtdd_topics.json"))
    router.get(f"{DTDD}/items").respond(status_code=404, json={"error": "not_found"})
    with pytest.raises(SourceNotFound):
        await dtdd.get_community("tt0000001")


async def test_timeout(router: respx.MockRouter, dtdd: DTDDService) -> None:
    router.get(f"{DTDD}/topics").mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(SourceUnavailable):
        await dtdd.get_community("tt15398776")


@pytest.mark.parametrize(("status", "fixture"), [(401, None), (403, "dtdd_error_403.json")])
async def test_auth_errors_unavailable(
    router: respx.MockRouter, dtdd: DTDDService, status: int, fixture: str | None
) -> None:
    router.get(f"{DTDD}/topics").respond(
        status_code=status, json=load_json(fixture) if fixture else {"error": "missing_api_key"}
    )
    with pytest.raises(SourceUnavailable) as info:
        await dtdd.get_community("tt15398776")
    assert info.value.reason in {"missing_api_key", "upgrade_required"}


async def test_429_long_retry_after_opens_circuit(
    router: respx.MockRouter, dtdd: DTDDService
) -> None:
    route = router.get(f"{DTDD}/topics").respond(
        status_code=429, json=load_json("dtdd_error_429.json"), headers={"Retry-After": "30"}
    )
    with pytest.raises(SourceUnavailable) as info:
        await dtdd.get_community("tt15398776")
    assert info.value.reason == "rate_limit_exceeded"
    # Retry-After süresince DTDD'ye hiç istek atılmaz.
    with pytest.raises(SourceUnavailable):
        await dtdd.get_community("tt15398776")
    assert route.call_count == 1


async def test_429_short_retry_after_is_honoured(
    router: respx.MockRouter, dtdd: DTDDService
) -> None:
    route = router.get(f"{DTDD}/topics").mock(
        side_effect=[
            httpx.Response(
                429, json=load_json("dtdd_error_429.json"), headers={"Retry-After": "0"}
            ),
            httpx.Response(200, json=load_json("dtdd_topics.json")),
        ]
    )
    topics = await dtdd.sensitive_topics()
    assert route.call_count == 2
    assert 108 in topics


async def test_monthly_limit_no_retry(router: respx.MockRouter, dtdd: DTDDService) -> None:
    route = router.get(f"{DTDD}/topics").respond(
        status_code=429, json=load_json("dtdd_error_monthly.json"), headers={"Retry-After": "1"}
    )
    with pytest.raises(SourceUnavailable) as info:
        await dtdd.sensitive_topics()
    assert info.value.reason == "monthly_limit_exceeded"
    assert route.call_count == 1


async def test_missing_api_key(client: httpx.AsyncClient, cache: InMemoryTTLCache) -> None:
    with pytest.raises(SourceUnavailable):
        await DTDDService(client, api_key="", cache=cache).get_community("tt15398776")
