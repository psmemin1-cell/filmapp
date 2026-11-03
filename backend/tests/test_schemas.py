from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.schemas.movie_response import MovieSearchResponse, VoteBreakdown

CONTRACT_EXAMPLE = {
    "query": "oppenheimer",
    "movie": {
        "tmdb_id": 872585,
        "imdb_id": "tt15398776",
        "title": "Oppenheimer",
        "original_title": "Oppenheimer",
        "year": 2023,
        "runtime_minutes": 181,
        "overview": "...",
        "poster_url": "https://image.tmdb.org/t/p/w500/x.jpg",
        "rating": 8.1,
        "rating_source": "tmdb",
        "rating_votes": 7421,
    },
    "streaming_tr": {
        "available": True,
        "flatrate": [{"name": "Netflix", "logo_url": "https://image.tmdb.org/t/p/w92/x.jpg"}],
        "rent": [],
        "buy": [],
        "tmdb_link": "https://www.themoviedb.org/movie/872585/watch?locale=TR",
    },
    "content_advisory": {
        "sex_nudity": {
            "severity": "Moderate",
            "vote_total": 412,
            "vote_breakdown": {"none": 0.12, "mild": 0.21, "moderate": 0.44, "severe": 0.23},
            "descriptions": ["...", "..."],
        },
        "other_categories": [{"name": "Violence & Gore", "severity": "Mild", "vote_total": 388}],
        "community": [
            {
                "topic_id": 108,
                "question": "Çıplaklık var mı?",
                "yes": 184,
                "no": 31,
                "yes_ratio": 0.856,
                "comment_count": 12,
                "notes": ["..."],
            }
        ],
        "attribution": "Powered by DoesTheDogDie.com",
    },
    "similar": [
        {
            "tmdb_id": 335984,
            "title": "Blade Runner 2049",
            "year": 2017,
            "poster_url": "https://image.tmdb.org/t/p/w342/x.jpg",
            "rating": 7.6,
        }
    ],
    "sources": {
        "tmdb": "ok",
        "imdb_parents_guide": "ok",
        "dtdd": "unavailable",
        "similar": "fallback",
    },
    "cached": False,
    "generated_at": "2026-11-03T12:04:11Z",
}


def test_contract_example_round_trips() -> None:
    model = MovieSearchResponse.model_validate(CONTRACT_EXAMPLE)
    dumped = model.model_dump(mode="json")
    assert dumped["generated_at"] == "2026-11-03T12:04:11Z"
    # Sözleşmedeki her alan aynı adla yanıtta bulunur (topic_key ek alandır).
    for key in CONTRACT_EXAMPLE:
        assert key in dumped
    community = dumped["content_advisory"]["community"][0]
    assert set(CONTRACT_EXAMPLE["content_advisory"]["community"][0]) <= set(community)
    assert community["topic_key"] is None


def test_nullable_blocks() -> None:
    data = {
        **CONTRACT_EXAMPLE,
        "streaming_tr": None,
        "content_advisory": None,
        "similar": None,
    }
    model = MovieSearchResponse.model_validate(data)
    assert model.streaming_tr is None and model.content_advisory is None and model.similar is None


def test_vote_breakdown_must_sum_to_one() -> None:
    VoteBreakdown(none=0.12, mild=0.21, moderate=0.44, severe=0.235)  # 1.005 tolerans içinde
    with pytest.raises(ValidationError):
        VoteBreakdown(none=0.5, mild=0.5, moderate=0.5, severe=0.0)


def test_vote_breakdown_rejects_percentages() -> None:
    with pytest.raises(ValidationError):
        VoteBreakdown(none=12, mild=21, moderate=44, severe=23)


@pytest.mark.parametrize("severity", ["mild", "Hafif", "MODERATE", "Extreme"])
def test_severity_only_four_values(severity: str) -> None:
    data = {**CONTRACT_EXAMPLE}
    data["content_advisory"] = {
        **CONTRACT_EXAMPLE["content_advisory"],
        "sex_nudity": {**CONTRACT_EXAMPLE["content_advisory"]["sex_nudity"], "severity": severity},
    }
    with pytest.raises(ValidationError):
        MovieSearchResponse.model_validate(data)


def test_invalid_source_status_rejected() -> None:
    data = {**CONTRACT_EXAMPLE, "sources": {**CONTRACT_EXAMPLE["sources"], "dtdd": "error"}}
    with pytest.raises(ValidationError):
        MovieSearchResponse.model_validate(data)


def test_generated_at_serialized_as_utc_z() -> None:
    model = MovieSearchResponse.model_validate(
        {**CONTRACT_EXAMPLE, "generated_at": datetime(2026, 1, 2, 3, 4, 5, 678, tzinfo=UTC)}
    )
    assert model.model_dump(mode="json")["generated_at"] == "2026-01-02T03:04:05Z"
