package com.cinescope.app.domain.repository

import com.cinescope.app.domain.model.MovieSearchResult

interface MovieRepository {
    suspend fun search(title: String): SearchOutcome

    /** Sunucuyu uyandırır; sonuç önemsizdir, hata yutulur. */
    suspend fun warmUp()
}

sealed interface SearchOutcome {
    data class Found(val result: MovieSearchResult) : SearchOutcome
    data object NotFound : SearchOutcome
    data class Failure(val type: FailureType) : SearchOutcome
}

enum class FailureType { NETWORK, SERVER, UNKNOWN }
