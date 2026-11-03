package com.cinescope.app.presentation.search

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.cinescope.app.R
import com.cinescope.app.domain.model.MovieSearchResult
import com.cinescope.app.domain.model.SimilarMovie
import com.cinescope.app.domain.repository.FailureType
import com.cinescope.app.presentation.components.CineSearchBar
import com.cinescope.app.presentation.components.ContentAdvisoryCard
import com.cinescope.app.presentation.components.MovieHeaderCard
import com.cinescope.app.presentation.components.ShimmerPlaceholder
import com.cinescope.app.presentation.components.SimilarMoviesRow
import com.cinescope.app.presentation.components.StreamingRow

@Composable
fun SearchScreen(viewModel: SearchViewModel = hiltViewModel()) {
    val query by viewModel.query.collectAsStateWithLifecycle()
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            CineSearchBar(
                query = query,
                onQueryChange = viewModel::onQueryChange,
                onSearch = viewModel::onSearch,
                onClear = viewModel::onClear,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
        },
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            when (val current = state) {
                SearchUiState.Idle -> MessageState(
                    title = stringResource(R.string.state_idle_title),
                    body = stringResource(R.string.state_idle_body),
                )
                is SearchUiState.Loading -> ShimmerPlaceholder()
                is SearchUiState.NotFound -> MessageState(
                    title = stringResource(R.string.state_not_found),
                    body = stringResource(R.string.state_not_found_hint),
                )
                is SearchUiState.Error -> ErrorState(type = current.type, onRetry = viewModel::onRetry)
                is SearchUiState.Success -> ResultContent(
                    result = current.result,
                    onSimilarClick = { viewModel.onSimilarMovieClick(it.title) },
                )
            }
        }
    }
}

@Composable
private fun ResultContent(result: MovieSearchResult, onSimilarClick: (SimilarMovie) -> Unit) {
    val listState = rememberLazyListState()
    // Yeni film geldiğinde (ör. benzer filme tıklandığında) en üste dön.
    LaunchedEffect(result.movie.tmdbId) { listState.scrollToItem(0) }
    LazyColumn(
        state = listState,
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item(key = "header") { MovieHeaderCard(movie = result.movie) }
        item(key = "streaming") { StreamingRow(block = result.streaming) }
        item(key = "advisory") {
            ContentAdvisoryCard(
                parentsGuide = result.parentsGuide,
                community = result.community,
                attribution = result.attribution,
            )
        }
        item(key = "similar") { SimilarMoviesRow(block = result.similar, onMovieClick = onSimilarClick) }
    }
}

@Composable
private fun MessageState(title: String, body: String) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(Modifier.height(48.dp))
        Text(text = title, style = MaterialTheme.typography.titleMedium, textAlign = TextAlign.Center)
        Spacer(Modifier.height(8.dp))
        Text(
            text = body,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center,
        )
    }
}

@Composable
private fun ErrorState(type: FailureType, onRetry: () -> Unit) {
    val message = when (type) {
        FailureType.NETWORK -> R.string.state_error_network
        FailureType.SERVER -> R.string.state_error_server
        FailureType.UNKNOWN -> R.string.state_error_unknown
    }
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Spacer(Modifier.height(48.dp))
        Text(
            text = stringResource(message),
            style = MaterialTheme.typography.bodyLarge,
            textAlign = TextAlign.Center,
        )
        Spacer(Modifier.height(16.dp))
        Button(onClick = onRetry) {
            Icon(Icons.Default.Refresh, contentDescription = null)
            Text(stringResource(R.string.action_retry), modifier = Modifier.padding(start = 8.dp))
        }
    }
}
