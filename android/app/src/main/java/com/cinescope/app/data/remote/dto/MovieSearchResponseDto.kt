package com.cinescope.app.data.remote.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/*
 * Backend sözleşmesinin (backend/app/schemas/movie_response.py) birebir karşılığı.
 * Alan adları sözleşmeyle aynıdır; DTO'lar UI'a taşınmaz, MovieMapper ile domain'e çevrilir.
 */

@Serializable
data class MovieSearchResponseDto(
    @SerialName("query") val query: String,
    @SerialName("movie") val movie: MovieDto,
    @SerialName("streaming_tr") val streamingTr: StreamingTrDto? = null,
    @SerialName("content_advisory") val contentAdvisory: ContentAdvisoryDto? = null,
    @SerialName("similar") val similar: List<SimilarMovieDto>? = null,
    @SerialName("sources") val sources: SourcesDto,
    @SerialName("cached") val cached: Boolean = false,
    @SerialName("generated_at") val generatedAt: String,
)

@Serializable
data class MovieDto(
    @SerialName("tmdb_id") val tmdbId: Int,
    @SerialName("imdb_id") val imdbId: String? = null,
    @SerialName("title") val title: String,
    @SerialName("original_title") val originalTitle: String? = null,
    @SerialName("year") val year: Int? = null,
    @SerialName("runtime_minutes") val runtimeMinutes: Int? = null,
    @SerialName("overview") val overview: String = "",
    @SerialName("poster_url") val posterUrl: String? = null,
    @SerialName("rating") val rating: Double? = null,
    @SerialName("rating_source") val ratingSource: String,
    @SerialName("rating_votes") val ratingVotes: Int? = null,
)

@Serializable
data class StreamingTrDto(
    @SerialName("available") val available: Boolean,
    @SerialName("flatrate") val flatrate: List<ProviderDto> = emptyList(),
    @SerialName("rent") val rent: List<ProviderDto> = emptyList(),
    @SerialName("buy") val buy: List<ProviderDto> = emptyList(),
    @SerialName("tmdb_link") val tmdbLink: String,
)

@Serializable
data class ProviderDto(
    @SerialName("name") val name: String,
    @SerialName("logo_url") val logoUrl: String? = null,
)

@Serializable
data class ContentAdvisoryDto(
    @SerialName("sex_nudity") val sexNudity: SexNudityDto? = null,
    @SerialName("other_categories") val otherCategories: List<AdvisoryCategoryDto>? = null,
    @SerialName("community") val community: List<CommunityTopicDto>? = null,
    @SerialName("attribution") val attribution: String,
)

@Serializable
data class SexNudityDto(
    @SerialName("severity") val severity: String? = null,
    @SerialName("vote_total") val voteTotal: Int = 0,
    @SerialName("vote_breakdown") val voteBreakdown: VoteBreakdownDto? = null,
    @SerialName("descriptions") val descriptions: List<String> = emptyList(),
)

@Serializable
data class VoteBreakdownDto(
    @SerialName("none") val none: Double,
    @SerialName("mild") val mild: Double,
    @SerialName("moderate") val moderate: Double,
    @SerialName("severe") val severe: Double,
)

@Serializable
data class AdvisoryCategoryDto(
    @SerialName("name") val name: String,
    @SerialName("severity") val severity: String? = null,
    @SerialName("vote_total") val voteTotal: Int = 0,
)

@Serializable
data class CommunityTopicDto(
    @SerialName("topic_id") val topicId: Int,
    @SerialName("topic_key") val topicKey: String? = null,
    @SerialName("question") val question: String,
    @SerialName("yes") val yes: Int,
    @SerialName("no") val no: Int,
    @SerialName("yes_ratio") val yesRatio: Double,
    @SerialName("comment_count") val commentCount: Int = 0,
    @SerialName("notes") val notes: List<String> = emptyList(),
)

@Serializable
data class SimilarMovieDto(
    @SerialName("tmdb_id") val tmdbId: Int,
    @SerialName("title") val title: String,
    @SerialName("year") val year: Int? = null,
    @SerialName("poster_url") val posterUrl: String? = null,
    @SerialName("rating") val rating: Double? = null,
)

@Serializable
data class SourcesDto(
    @SerialName("tmdb") val tmdb: String,
    @SerialName("imdb_parents_guide") val imdbParentsGuide: String,
    @SerialName("dtdd") val dtdd: String,
    @SerialName("similar") val similar: String,
)
