package com.cinescope.app.presentation.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.painter.ColorPainter
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import com.cinescope.app.R
import com.cinescope.app.domain.model.Block
import com.cinescope.app.domain.model.SimilarMovie

@Composable
fun SimilarMoviesRow(
    block: Block<List<SimilarMovie>>,
    onMovieClick: (SimilarMovie) -> Unit,
    modifier: Modifier = Modifier,
) {
    SectionCard(title = stringResource(R.string.similar_title), modifier = modifier) {
        when (block) {
            is Block.Missing -> NoDataContent(block.reason)
            is Block.Ready -> LazyRow(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                items(block.data, key = { it.tmdbId }) { movie ->
                    SimilarMovieCard(movie = movie, onClick = { onMovieClick(movie) })
                }
            }
        }
    }
}

@Composable
private fun SimilarMovieCard(movie: SimilarMovie, onClick: () -> Unit) {
    val placeholder = ColorPainter(MaterialTheme.colorScheme.surfaceVariant)
    Card(onClick = onClick, modifier = Modifier.width(120.dp)) {
        Column {
            AsyncImage(
                model = movie.posterUrl,
                contentDescription = stringResource(R.string.poster_description, movie.title),
                placeholder = placeholder,
                error = placeholder,
                fallback = placeholder,
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(170.dp)
                    .clip(RoundedCornerShape(topStart = 12.dp, topEnd = 12.dp)),
            )
            Column(modifier = Modifier.padding(8.dp)) {
                Text(
                    text = movie.title,
                    style = MaterialTheme.typography.labelLarge,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                movie.year?.let {
                    Text(
                        text = it.toString(),
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}
