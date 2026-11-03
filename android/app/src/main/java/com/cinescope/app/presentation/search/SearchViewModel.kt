package com.cinescope.app.presentation.search

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.cinescope.app.domain.repository.MovieRepository
import com.cinescope.app.domain.repository.SearchOutcome
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.FlowPreview
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.debounce
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.drop
import kotlinx.coroutines.flow.filter
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.merge
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class SearchViewModel @Inject constructor(
    private val repository: MovieRepository,
) : ViewModel() {

    private val _query = MutableStateFlow("")
    val query: StateFlow<String> = _query.asStateFlow()

    private val _uiState = MutableStateFlow<SearchUiState>(SearchUiState.Idle)
    val uiState: StateFlow<SearchUiState> = _uiState.asStateFlow()

    /** Klavye "ara" aksiyonu, yeniden dene ve benzer film tıklaması: debounce'u atlar. */
    private val immediate = MutableSharedFlow<SearchRequest>(extraBufferCapacity = 1)

    private data class SearchRequest(val query: String, val forced: Boolean)

    init {
        // Kullanıcı yazarken sunucu uyansın (ücretsiz barındırmada ilk istek yavaştır).
        viewModelScope.launch { repository.warmUp() }
        observeSearches()
    }

    @OptIn(FlowPreview::class)
    private fun observeSearches() {
        val debounced = _query
            .drop(1)
            .map { it.trim() }
            .debounce(DEBOUNCE_MS)
            .filter { it.isEmpty() || it.length >= MIN_QUERY_LENGTH }
            .map { SearchRequest(it, forced = false) }

        viewModelScope.launch {
            merge(debounced, immediate)
                // Aynı metin için debounce tekrar tetiklemesin; zorunlu istekler her zaman geçer.
                .distinctUntilChanged { old, new -> !new.forced && old.query == new.query }
                .collectLatest { request -> execute(request.query) }
        }
    }

    fun onQueryChange(value: String) {
        _query.value = value
    }

    fun onSearch() {
        submit(_query.value)
    }

    fun onClear() {
        _query.value = ""
        immediate.tryEmit(SearchRequest("", forced = true))
    }

    fun onRetry() {
        val current = when (val state = _uiState.value) {
            is SearchUiState.Error -> state.query
            else -> _query.value
        }
        submit(current)
    }

    fun onSimilarMovieClick(title: String) {
        _query.value = title
        submit(title)
    }

    private fun submit(raw: String) {
        immediate.tryEmit(SearchRequest(raw.trim(), forced = true))
    }

    private suspend fun execute(query: String) {
        if (query.isEmpty()) {
            _uiState.value = SearchUiState.Idle
            return
        }
        _uiState.value = SearchUiState.Loading(query)
        _uiState.value = when (val outcome = repository.search(query)) {
            is SearchOutcome.Found -> SearchUiState.Success(outcome.result)
            SearchOutcome.NotFound -> SearchUiState.NotFound(query)
            is SearchOutcome.Failure -> SearchUiState.Error(query, outcome.type)
        }
    }

    private companion object {
        const val DEBOUNCE_MS = 400L
        const val MIN_QUERY_LENGTH = 2
    }
}
