package com.cinescope.app.presentation.components

import androidx.annotation.StringRes
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.KeyboardArrowUp
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.cinescope.app.R

/**
 * Hassas içerik açıklamaları. Kasıtlı olarak KAPALI başlar; kullanıcı açıkça
 * "Detayları göster"e basmadan metin görünmez.
 */
@Composable
fun ExpandableDescriptions(
    items: List<String>,
    modifier: Modifier = Modifier,
    @StringRes showLabel: Int = R.string.descriptions_show,
    @StringRes hideLabel: Int = R.string.descriptions_hide,
) {
    if (items.isEmpty()) return
    var expanded by rememberSaveable(items) { mutableStateOf(false) }
    Column(modifier = modifier) {
        TextButton(onClick = { expanded = !expanded }) {
            Text(stringResource(if (expanded) hideLabel else showLabel))
            Icon(
                imageVector = if (expanded) Icons.Default.KeyboardArrowUp else Icons.Default.KeyboardArrowDown,
                contentDescription = null,
            )
        }
        AnimatedVisibility(visible = expanded) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items.forEach { item ->
                    Text(text = "• $item", style = MaterialTheme.typography.bodySmall)
                }
            }
        }
    }
}
