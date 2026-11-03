package com.cinescope.app.presentation.components

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AssistChip
import androidx.compose.material3.AssistChipDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.painter.ColorPainter
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import coil3.compose.AsyncImage
import com.cinescope.app.R
import com.cinescope.app.domain.model.Block
import com.cinescope.app.domain.model.Provider
import com.cinescope.app.domain.model.Streaming

@Composable
fun StreamingRow(block: Block<Streaming>, modifier: Modifier = Modifier) {
    SectionCard(title = stringResource(R.string.streaming_title), modifier = modifier) {
        when (block) {
            is Block.Missing -> NoDataContent(block.reason)
            is Block.Ready -> StreamingContent(block.data)
        }
    }
}

@Composable
private fun StreamingContent(streaming: Streaming) {
    if (!streaming.available) {
        Text(
            text = stringResource(R.string.streaming_not_available),
            style = MaterialTheme.typography.bodyMedium,
        )
        return
    }
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        ProviderGroup(R.string.streaming_flatrate, streaming.flatrate)
        ProviderGroup(R.string.streaming_rent, streaming.rent)
        ProviderGroup(R.string.streaming_buy, streaming.buy)
        val uriHandler = LocalUriHandler.current
        TextButton(onClick = { uriHandler.openUri(streaming.tmdbLink) }) {
            Text(stringResource(R.string.streaming_open_tmdb))
        }
        Text(
            text = stringResource(R.string.streaming_attribution),
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun ProviderGroup(titleRes: Int, providers: List<Provider>) {
    if (providers.isEmpty()) return
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(
            text = stringResource(titleRes),
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            items(providers, key = { it.name }) { provider -> ProviderChip(provider) }
        }
    }
}

@Composable
private fun ProviderChip(provider: Provider) {
    val placeholder = ColorPainter(MaterialTheme.colorScheme.surfaceVariant)
    AssistChip(
        onClick = {},
        label = { Text(provider.name) },
        leadingIcon = {
            AsyncImage(
                model = provider.logoUrl,
                contentDescription = stringResource(R.string.provider_logo_description, provider.name),
                placeholder = placeholder,
                error = placeholder,
                fallback = placeholder,
                modifier = Modifier
                    .size(AssistChipDefaults.IconSize)
                    .clip(RoundedCornerShape(4.dp)),
            )
        },
    )
}
