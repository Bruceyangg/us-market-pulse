package com.bruceyangg.pulsedesk.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/** Chinese tape convention: red = up, green = down. */
val TapeUp = Color(0xFFD92B2B)
val TapeDown = Color(0xFF0F8A6A)
val Ink = Color(0xFFF4F7FB)
val InkSoft = Color(0xFF9AABBD)
val Panel = Color(0xFF151C26)
val PanelElevated = Color(0xFF1C2532)
val Line = Color(0xFF2A3544)
val Accent = Color(0xFF3D8FBF)

private val DarkColors = darkColorScheme(
    primary = Accent,
    onPrimary = Color.White,
    secondary = TapeUp,
    background = Color(0xFF0E141B),
    onBackground = Ink,
    surface = Panel,
    onSurface = Ink,
    surfaceVariant = PanelElevated,
    onSurfaceVariant = InkSoft,
    outline = Line,
    error = TapeUp,
)

private val LightColors = lightColorScheme(
    primary = Color(0xFF1F6F9A),
    onPrimary = Color.White,
    secondary = TapeUp,
    background = Color(0xFFF3F5F8),
    onBackground = Color(0xFF15202B),
    surface = Color.White,
    onSurface = Color(0xFF15202B),
    surfaceVariant = Color(0xFFE8EEF5),
    onSurfaceVariant = Color(0xFF5A6B7C),
    outline = Color(0xFFCDD6E0),
    error = TapeUp,
)

@Composable
fun PulseDeskTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    val colors = if (darkTheme) DarkColors else LightColors
    MaterialTheme(
        colorScheme = colors,
        typography = MaterialTheme.typography.copy(
            headlineLarge = TextStyle(
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.Bold,
                fontSize = 28.sp,
                letterSpacing = (-0.5).sp,
            ),
            titleLarge = TextStyle(
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.SemiBold,
                fontSize = 20.sp,
            ),
            titleMedium = TextStyle(
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.SemiBold,
                fontSize = 16.sp,
            ),
            bodyMedium = TextStyle(
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.Normal,
                fontSize = 14.sp,
            ),
            labelLarge = TextStyle(
                fontFamily = FontFamily.SansSerif,
                fontWeight = FontWeight.SemiBold,
                fontSize = 13.sp,
            ),
        ),
        content = content,
    )
}

fun tapeColor(pct: Double?): Color = when {
    pct == null -> InkSoft
    pct > 0 -> TapeUp
    pct < 0 -> TapeDown
    else -> InkSoft
}

fun heatColor(pct: Double?): Color {
    if (pct == null) return Color(0xFF2A3340)
    val t = (pct / 3.5).coerceIn(-1.0, 1.0)
    return if (t >= 0) {
        lerp(Color(0xFF2A3340), TapeUp, (0.22 + t * 0.78).toFloat())
    } else {
        lerp(Color(0xFF2A3340), TapeDown, (0.22 + -t * 0.78).toFloat())
    }
}

private fun lerp(a: Color, b: Color, t: Float): Color {
    val x = t.coerceIn(0f, 1f)
    return Color(
        red = a.red + (b.red - a.red) * x,
        green = a.green + (b.green - a.green) * x,
        blue = a.blue + (b.blue - a.blue) * x,
        alpha = 1f,
    )
}
