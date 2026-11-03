package com.cinescope.app.presentation.components

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.cinescope.app.R
import com.cinescope.app.domain.model.MissingReason

/** Bir kartın "veri yok" hali. Kartın başlığı ve çerçevesi korunur, içerik yerine bu gösterilir. */
@Composable
fun NoDataContent(reason: MissingReason, modifier: Modifier = Modifier) {
    Column(modifier = modifier) {
        Text(
            text = stringResource(R.string.block_no_data),
            style = MaterialTheme.typography.labelLarge,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        Spacer(Modifier.height(2.dp))
        Text(
            text = stringResource(reason.messageRes()),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
fun SourceUnavailableCard(title: String, reason: MissingReason, modifier: Modifier = Modifier) {
    SectionCard(title = title, modifier = modifier) {
        NoDataContent(reason)
    }
}
