package com.cinescope.app.presentation.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.Icon
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
import com.cinescope.app.domain.model.Movie

private const val MINUTES_PER_HOUR = 60
private const val OVERVIEW_MAX_LINES = 4

@Composable
fun MovieHeaderCard(movie: Movie, modifier: Modifier = Modifier) {
    Card(modifier = modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Poster(
                url = movie.posterUrl,
                contentDescription = stringResource(R.string.poster_description, movie.title),
            )
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(
                    text = movie.title,
                    style = MaterialTheme.typography.titleLarge,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                movie.originalTitle?.let {
                    Text(
                        text = it,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                MetaLine(year = movie.year, runtimeMinutes = movie.runtimeMinutes)
                RatingBadge(rating = movie.rating, source = movie.ratingSource, votes = movie.ratingVotes)
                if (movie.overview.isNotBlank()) {
                    Text(
                        text = movie.overview,
                        style = MaterialTheme.typography.bodySmall,
                        maxLines = OVERVIEW_MAX_LINES,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}

@Composable
private fun Poster(url: String?, contentDescription: String) {
    val placeholder = ColorPainter(MaterialTheme.colorScheme.surfaceVariant)
    AsyncImage(
        model = url,
        contentDescription = contentDescription,
        placeholder = placeholder,
        error = placeholder,
        fallback = placeholder,
        contentScale = ContentScale.Crop,
        modifier = Modifier
            .size(width = 100.dp, height = 150.dp)
            .clip(RoundedCornerShape(8.dp)),
    )
}

@Composable
private fun MetaLine(year: Int?, runtimeMinutes: Int?) {
    val runtime = runtimeMinutes?.let { minutes ->
        val hours = minutes / MINUTES_PER_HOUR
        val rest = minutes % MINUTES_PER_HOUR
        if (hours > 0) {
            stringResource(R.string.runtime_hours_minutes, hours, rest)
        } else {
            stringResource(R.string.runtime_minutes, rest)
        }
    }
    val parts = listOfNotNull(year?.toString(), runtime)
    if (parts.isNotEmpty()) {
        Text(
            text = parts.joinToString(separator = " · "),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

/** Rozet etiketi `rating_source` alanından gelir (ör. "tmdb" -> "TMDB"); sabit "IMDb" yazılmaz. */
@Composable
private fun RatingBadge(rating: Double?, source: String, votes: Int?) {
    val label = if (rating != null) {
        stringResource(R.string.rating_badge, source.uppercase(), rating)
    } else {
        stringResource(R.string.rating_missing)
    }
    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        AssistChip(
            onClick = {},
            enabled = false,
            label = { Text(label) },
            leadingIcon = {
                Icon(
                    imageVector = Icons.Default.Star,
                    contentDescription = null,
                    modifier = Modifier.size(AssistChipDefaults.IconSize),
                )
            },
            colors = AssistChipDefaults.assistChipColors(
                disabledContainerColor = MaterialTheme.colorScheme.secondaryContainer,
                disabledLabelColor = MaterialTheme.colorScheme.onSecondaryContainer,
                disabledLeadingIconContentColor = MaterialTheme.colorScheme.onSecondaryContainer,
            ),
            border = null,
        )
        if (rating != null && votes != null && votes > 0) {
            Text(
                text = stringResource(R.string.rating_votes, votes),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 14.dp),
            )
        }
    }
}
