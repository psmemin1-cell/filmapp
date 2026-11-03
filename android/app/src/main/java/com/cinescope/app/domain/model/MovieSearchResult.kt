package com.cinescope.app.domain.model

/** Bir arama sonucunun UI'a hazır domain karşılığı. */
data class MovieSearchResult(
    val query: String,
    val movie: Movie,
    val streaming: Block<Streaming>,
    val parentsGuide: Block<ParentsGuide>,
    val community: Block<List<CommunityTopic>>,
    val similar: Block<List<SimilarMovie>>,
    val attribution: String,
    val cached: Boolean,
)

/**
 * Blok bazlı kısmi durum. Ana veri (Movie) geldiğinde her kart kendi bloğuna bakarak
 * veri ya da "veri yok" halini gösterir.
 */
sealed interface Block<out T> {
    data class Ready<T>(val data: T, val isFallback: Boolean = false) : Block<T>
    data class Missing(val reason: MissingReason) : Block<Nothing>
}

enum class MissingReason {
    /** Dış servis hatası/timeout (sources = "unavailable" veya blok null). */
    UNAVAILABLE,

    /** Kaynak filmi tanımıyor (sources = "not_found"). */
    NOT_FOUND,
}

data class Movie(
    val tmdbId: Int,
    val imdbId: String?,
    val title: String,
    val originalTitle: String?,
    val year: Int?,
    val runtimeMinutes: Int?,
    val overview: String,
    val posterUrl: String?,
    val rating: Double?,
    val ratingSource: String,
    val ratingVotes: Int?,
)

data class Streaming(
    val available: Boolean,
    val flatrate: List<Provider>,
    val rent: List<Provider>,
    val buy: List<Provider>,
    val tmdbLink: String,
)

data class Provider(val name: String, val logoUrl: String?)

enum class Severity { NONE, MILD, MODERATE, SEVERE }

data class VoteBreakdown(
    val none: Float,
    val mild: Float,
    val moderate: Float,
    val severe: Float,
) {
    fun forSeverity(severity: Severity): Float = when (severity) {
        Severity.NONE -> none
        Severity.MILD -> mild
        Severity.MODERATE -> moderate
        Severity.SEVERE -> severe
    }
}

data class ParentsGuide(
    /** Sex & Nudity; IMDb'de bu kategori yoksa null. */
    val sexNudity: SexNudity?,
    val otherCategories: List<AdvisoryCategory>,
)

data class SexNudity(
    val severity: Severity?,
    val voteTotal: Int,
    val voteBreakdown: VoteBreakdown?,
    val descriptions: List<String>,
)

enum class AdvisoryCategoryType { VIOLENCE, PROFANITY, ALCOHOL, FRIGHTENING, OTHER }

data class AdvisoryCategory(
    val type: AdvisoryCategoryType,
    /** Backend'in özgün (İngilizce) adı; OTHER için gösterilir. */
    val rawName: String,
    val severity: Severity?,
    val voteTotal: Int,
)

enum class CommunityTopicKey { NUDITY, SEX_SCENE, SEXUAL_ASSAULT, OTHER }

data class CommunityTopic(
    val topicId: Int,
    val key: CommunityTopicKey,
    /** DTDD'nin özgün sorusu; key OTHER ise gösterilir. */
    val rawQuestion: String,
    val yes: Int,
    val no: Int,
    val yesRatio: Float,
    val commentCount: Int,
    val notes: List<String>,
)

data class SimilarMovie(
    val tmdbId: Int,
    val title: String,
    val year: Int?,
    val posterUrl: String?,
    val rating: Double?,
)
