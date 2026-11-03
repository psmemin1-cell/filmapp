package com.cinescope.app.presentation.theme

import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.toArgb
import androidx.core.graphics.ColorUtils
import com.cinescope.app.domain.model.Severity

/**
 * Severity renkleri sabit hex yerine aktif [ColorScheme]'den türetilir: `error` rolü (kırmızı)
 * ve konteyner tonları alınır, yalnızca ton (hue) döndürülerek turuncu, sarı ve yeşil elde
 * edilir. Böylece açık/koyu tema ve dinamik renkte kontrast seviyesi korunur.
 */
@Immutable
data class SeverityColors(
    val none: SeverityTone,
    val mild: SeverityTone,
    val moderate: SeverityTone,
    val severe: SeverityTone,
    val unknown: SeverityTone,
) {
    fun of(severity: Severity?): SeverityTone = when (severity) {
        Severity.NONE -> none
        Severity.MILD -> mild
        Severity.MODERATE -> moderate
        Severity.SEVERE -> severe
        null -> unknown
    }

    companion object {
        private const val HUE_ORANGE = 30f
        private const val HUE_YELLOW = 52f
        private const val HUE_GREEN = 125f

        fun from(scheme: ColorScheme): SeverityColors {
            fun tone(shift: Float) = SeverityTone(
                accent = scheme.error.rotateHue(shift),
                container = scheme.errorContainer.rotateHue(shift),
                onContainer = scheme.onErrorContainer.rotateHue(shift),
            )
            return SeverityColors(
                none = tone(HUE_GREEN),
                mild = tone(HUE_YELLOW),
                moderate = tone(HUE_ORANGE),
                severe = SeverityTone(
                    accent = scheme.error,
                    container = scheme.errorContainer,
                    onContainer = scheme.onErrorContainer,
                ),
                unknown = SeverityTone(
                    accent = scheme.outline,
                    container = scheme.surfaceVariant,
                    onContainer = scheme.onSurfaceVariant,
                ),
            )
        }
    }
}

@Immutable
data class SeverityTone(val accent: Color, val container: Color, val onContainer: Color)

private fun Color.rotateHue(degrees: Float): Color {
    val hsl = FloatArray(3)
    ColorUtils.colorToHSL(toArgb(), hsl)
    hsl[0] = (hsl[0] + degrees).mod(360f)
    return Color(ColorUtils.HSLToColor(hsl)).copy(alpha = alpha)
}

val LocalSeverityColors = staticCompositionLocalOf<SeverityColors> {
    error("SeverityColors sağlanmadı: CineScopeTheme içinde kullanın")
}

val MaterialTheme.severityColors: SeverityColors
    @Composable
    @ReadOnlyComposable
    get() = LocalSeverityColors.current
