package com.cinescope.app.presentation.search

import com.cinescope.app.domain.model.MovieSearchResult
import com.cinescope.app.domain.repository.FailureType

sealed interface SearchUiState {
    data object Idle : SearchUiState
    data class Loading(val query: String) : SearchUiState
    data class Success(val result: MovieSearchResult) : SearchUiState
    data class Error(val query: String, val type: FailureType) : SearchUiState
    data class NotFound(val query: String) : SearchUiState
}
