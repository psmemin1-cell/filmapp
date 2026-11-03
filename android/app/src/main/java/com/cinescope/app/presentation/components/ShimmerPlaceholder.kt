package com.cinescope.app.presentation.components

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.cinescope.app.R

@Composable
private fun shimmerBrush(): Brush {
    val base = MaterialTheme.colorScheme.surfaceVariant
    val highlight = MaterialTheme.colorScheme.surface
    val transition = rememberInfiniteTransition(label = "shimmer")
    val offset by transition.animateFloat(
        initialValue = 0f,
        targetValue = 1200f,
        animationSpec = infiniteRepeatable(tween(1100, easing = LinearEasing), RepeatMode.Restart),
        label = "shimmerOffset",
    )
    return Brush.linearGradient(
        colors = listOf(base, highlight, base),
        start = Offset(offset - 400f, 0f),
        end = Offset(offset, 0f),
    )
}

@Composable
private fun ShimmerBox(width: Dp?, height: Dp, brush: Brush) {
    val sized = if (width != null) Modifier.width(width) else Modifier.fillMaxWidth()
    Box(
        modifier = sized
            .height(height)
            .clip(RoundedCornerShape(8.dp))
            .background(brush),
    )
}

/** Yükleme sırasında dört bloğun iskeleti. */
@Composable
fun ShimmerPlaceholder(modifier: Modifier = Modifier) {
    val brush = shimmerBrush()
    val description = stringResource(R.string.state_loading)
    Column(
        modifier = modifier
            .padding(16.dp)
            .semantics { contentDescription = description },
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
            Box(
                Modifier
                    .size(width = 100.dp, height = 150.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .background(brush),
            )
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                ShimmerBox(width = 180.dp, height = 22.dp, brush = brush)
                ShimmerBox(width = 120.dp, height = 16.dp, brush = brush)
                ShimmerBox(width = 72.dp, height = 28.dp, brush = brush)
            }
        }
        repeat(3) {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                ShimmerBox(width = 160.dp, height = 18.dp, brush = brush)
                ShimmerBox(width = null, height = 64.dp, brush = brush)
            }
        }
    }
}
