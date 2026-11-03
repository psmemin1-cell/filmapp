package com.cinescope.app.data.mapper

import com.cinescope.app.data.remote.dto.AdvisoryCategoryDto
import com.cinescope.app.data.remote.dto.CommunityTopicDto
import com.cinescope.app.data.remote.dto.MovieDto
import com.cinescope.app.data.remote.dto.MovieSearchResponseDto
import com.cinescope.app.data.remote.dto.ProviderDto
import com.cinescope.app.data.remote.dto.SexNudityDto
import com.cinescope.app.data.remote.dto.SimilarMovieDto
import com.cinescope.app.data.remote.dto.StreamingTrDto
import com.cinescope.app.domain.model.AdvisoryCategory
import com.cinescope.app.domain.model.AdvisoryCategoryType
import com.cinescope.app.domain.model.Block
import com.cinescope.app.domain.model.CommunityTopic
import com.cinescope.app.domain.model.CommunityTopicKey
import com.cinescope.app.domain.model.MissingReason
import com.cinescope.app.domain.model.Movie
import com.cinescope.app.domain.model.MovieSearchResult
import com.cinescope.app.domain.model.ParentsGuide
import com.cinescope.app.domain.model.Provider
import com.cinescope.app.domain.model.Severity
import com.cinescope.app.domain.model.SexNudity
import com.cinescope.app.domain.model.SimilarMovie
import com.cinescope.app.domain.model.Streaming
import com.cinescope.app.domain.model.VoteBreakdown

/** Backend `sources` değerleri. */
private object SourceStatus {
    const val OK = "ok"
    const val NOT_FOUND = "not_found"
    const val FALLBACK = "fallback"
}

/**
 * Blok kararı `sources` durumu VE alanın null olup olmadığı birlikte kontrol edilerek verilir:
 * yalnızca durum ok/fallback ve veri null değilse Ready.
 */
internal fun <D, T> resolveBlock(status: String, data: D?, map: (D) -> T): Block<T> {
    val usable = status == SourceStatus.OK || status == SourceStatus.FALLBACK
    return when {
        usable && data != null -> Block.Ready(map(data), isFallback = status == SourceStatus.FALLBACK)
        status == SourceStatus.NOT_FOUND -> Block.Missing(MissingReason.NOT_FOUND)
        else -> Block.Missing(MissingReason.UNAVAILABLE)
    }
}

fun MovieSearchResponseDto.toDomain(): MovieSearchResult {
    val advisory = contentAdvisory
    return MovieSearchResult(
        query = query,
        movie = movie.toDomain(),
        streaming = resolveBlock(sources.tmdb, streamingTr) { it.toDomain() },
        parentsGuide = resolveBlock(sources.imdbParentsGuide, advisory?.otherCategories) { others ->
            ParentsGuide(
                sexNudity = advisory?.sexNudity?.toDomain(),
                otherCategories = others.map { it.toDomain() },
            )
        },
        community = resolveBlock(sources.dtdd, advisory?.community) { topics ->
            topics.map { it.toDomain() }
        },
        similar = resolveBlock(sources.similar, similar) { list -> list.map { it.toDomain() } },
        attribution = advisory?.attribution ?: DTDD_ATTRIBUTION,
        cached = cached,
    )
}

const val DTDD_ATTRIBUTION = "Powered by DoesTheDogDie.com"

fun MovieDto.toDomain() = Movie(
    tmdbId = tmdbId,
    imdbId = imdbId,
    title = title,
    originalTitle = originalTitle?.takeIf { it != title },
    year = year,
    runtimeMinutes = runtimeMinutes,
    overview = overview,
    posterUrl = posterUrl,
    rating = rating,
    ratingSource = ratingSource,
    ratingVotes = ratingVotes,
)

fun StreamingTrDto.toDomain() = Streaming(
    available = available,
    flatrate = flatrate.map { it.toDomain() },
    rent = rent.map { it.toDomain() },
    buy = buy.map { it.toDomain() },
    tmdbLink = tmdbLink,
)

fun ProviderDto.toDomain() = Provider(name = name, logoUrl = logoUrl)

fun SexNudityDto.toDomain() = SexNudity(
    severity = severity.toSeverity(),
    voteTotal = voteTotal,
    voteBreakdown = voteBreakdown?.let {
        VoteBreakdown(
            none = it.none.toFloat().coerceIn(0f, 1f),
            mild = it.mild.toFloat().coerceIn(0f, 1f),
            moderate = it.moderate.toFloat().coerceIn(0f, 1f),
            severe = it.severe.toFloat().coerceIn(0f, 1f),
        )
    },
    descriptions = descriptions,
)

fun AdvisoryCategoryDto.toDomain() = AdvisoryCategory(
    type = when (name) {
        "Violence & Gore" -> AdvisoryCategoryType.VIOLENCE
        "Profanity" -> AdvisoryCategoryType.PROFANITY
        "Alcohol, Drugs & Smoking" -> AdvisoryCategoryType.ALCOHOL
        "Frightening & Intense Scenes" -> AdvisoryCategoryType.FRIGHTENING
        else -> AdvisoryCategoryType.OTHER
    },
    rawName = name,
    severity = severity.toSeverity(),
    voteTotal = voteTotal,
)

fun CommunityTopicDto.toDomain() = CommunityTopic(
    topicId = topicId,
    key = when (topicKey) {
        "nudity" -> CommunityTopicKey.NUDITY
        "sex_scene" -> CommunityTopicKey.SEX_SCENE
        "sexual_assault" -> CommunityTopicKey.SEXUAL_ASSAULT
        else -> CommunityTopicKey.OTHER
    },
    rawQuestion = question,
    yes = yes,
    no = no,
    yesRatio = yesRatio.toFloat().coerceIn(0f, 1f),
    commentCount = commentCount,
    notes = notes,
)

fun SimilarMovieDto.toDomain() = SimilarMovie(
    tmdbId = tmdbId,
    title = title,
    year = year,
    posterUrl = posterUrl,
    rating = rating,
)

/** Backend yalnızca "None" | "Mild" | "Moderate" | "Severe" | null döner; çeviri UI'da. */
fun String?.toSeverity(): Severity? = when (this) {
    "None" -> Severity.NONE
    "Mild" -> Severity.MILD
    "Moderate" -> Severity.MODERATE
    "Severe" -> Severity.SEVERE
    else -> null
}
