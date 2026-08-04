package com.bruceyangg.pulsedesk.ui.components

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.unit.dp
import com.bruceyangg.pulsedesk.data.model.ChartPoint
import com.bruceyangg.pulsedesk.ui.theme.TapeDown
import com.bruceyangg.pulsedesk.ui.theme.TapeUp
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

private data class MaSpec(val n: Int, val color: androidx.compose.ui.graphics.Color)

private val MaSpecs = listOf(
    MaSpec(5, androidx.compose.ui.graphics.Color(0xFFC47A16)),
    MaSpec(10, androidx.compose.ui.graphics.Color(0xFF2F6F9F)),
    MaSpec(30, androidx.compose.ui.graphics.Color(0xFF0F8A6A)),
    MaSpec(60, androidx.compose.ui.graphics.Color(0xFFA35C2A)),
    MaSpec(120, androidx.compose.ui.graphics.Color(0xFFB42318)),
    MaSpec(250, androidx.compose.ui.graphics.Color(0xFF3A4D63)),
)

@Composable
fun CandleChart(
    points: List<ChartPoint>,
    modifier: Modifier = Modifier,
    showMa: Boolean = true,
    lineMode: Boolean = false,
) {
    val bars = remember(points) {
        points.filter {
            if (lineMode) it.v != null || it.c != null
            else listOf(it.o, it.h, it.l, it.c).all { v -> v != null }
        }
    }
    if (bars.size < 2) {
        androidx.compose.material3.Text(
            "暂无走势数据",
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = modifier.height(180.dp),
        )
        return
    }

    var start by remember(bars.size) { mutableIntStateOf(0) }
    var count by remember(bars.size) { mutableIntStateOf(bars.size) }
    var scaleAcc by remember { mutableFloatStateOf(1f) }

    Canvas(
        modifier = modifier
            .fillMaxWidth()
            .height(220.dp)
            .pointerInput(bars.size) {
                detectTransformGestures { _, pan, zoom, _ ->
                    scaleAcc *= zoom
                    if (scaleAcc > 1.08f || scaleAcc < 0.92f) {
                        val factor = if (scaleAcc > 1f) 1.18f else 1 / 1.18f
                        scaleAcc = 1f
                        val pivot = 0.85f
                        val pivotIdx = start + pivot * count
                        val nextCount = (count / factor).roundToInt()
                            .coerceIn(min(12, bars.size), bars.size)
                        val nextStart = (pivotIdx - pivot * nextCount).roundToInt()
                            .coerceIn(0, bars.size - nextCount)
                        start = nextStart
                        count = nextCount
                    }
                    if (count < bars.size && kotlin.math.abs(pan.x) > 2f) {
                        val step = max(1, (count * 0.04f).roundToInt())
                        val dir = if (pan.x < 0) step else -step
                        start = (start + dir).coerceIn(0, bars.size - count)
                    }
                }
            },
    ) {
        val end = (start + count).coerceAtMost(bars.size)
        val view = bars.subList(start, end)
        val padX = 8f
        val padY = 12f
        val w = size.width
        val h = size.height

        if (lineMode) {
            val vals = view.map { (it.v ?: it.c)!!.toFloat() }
            val minV = vals.minOrNull() ?: return@Canvas
            val maxV = vals.maxOrNull() ?: return@Canvas
            val span = (maxV - minV).takeIf { it > 0f } ?: 1f
            val stepX = (w - padX * 2) / (vals.size - 1).coerceAtLeast(1)
            val path = Path()
            vals.forEachIndexed { i, v ->
                val x = padX + i * stepX
                val y = padY + (1f - (v - minV) / span) * (h - padY * 2)
                if (i == 0) path.moveTo(x, y) else path.lineTo(x, y)
            }
            val up = vals.last() >= vals.first()
            drawPath(path, if (up) TapeUp else TapeDown, style = Stroke(width = 3.5f, cap = StrokeCap.Round))
            return@Canvas
        }

        val closes = bars.map { it.c!!.toDouble() }
        val maLines = if (showMa) {
            MaSpecs.mapNotNull { spec ->
                if (closes.size < spec.n) return@mapNotNull null
                val series = sma(closes, spec.n).subList(start, end)
                if (series.none { it != null }) null else spec to series
            }
        } else emptyList()

        val highs = view.map { it.h!!.toFloat() }
        val lows = view.map { it.l!!.toFloat() }
        val maVals = maLines.flatMap { it.second.mapNotNull { v -> v?.toFloat() } }
        val minP = min(lows.minOrNull() ?: 0f, maVals.minOrNull() ?: Float.MAX_VALUE)
        val maxP = max(highs.maxOrNull() ?: 0f, maVals.maxOrNull() ?: Float.MIN_VALUE)
        val span = (maxP - minP).takeIf { it > 0f } ?: 1f
        fun yOf(price: Float) = padY + (1f - (price - minP) / span) * (h - padY * 2)

        val slot = (w - padX * 2) / view.size
        val bodyW = (slot * 0.62f).coerceIn(1.5f, 10f)

        view.forEachIndexed { i, b ->
            val o = b.o!!.toFloat()
            val hi = b.h!!.toFloat()
            val lo = b.l!!.toFloat()
            val c = b.c!!.toFloat()
            val up = c >= o
            val color = if (up) TapeUp else TapeDown
            val x = padX + i * slot + slot / 2f
            drawLine(color, Offset(x, yOf(hi)), Offset(x, yOf(lo)), strokeWidth = 2f)
            val top = min(yOf(o), yOf(c))
            val bodyH = max(2f, kotlin.math.abs(yOf(c) - yOf(o)))
            drawRect(color, Offset(x - bodyW / 2f, top), Size(bodyW, bodyH))
        }

        maLines.forEach { (spec, values) ->
            val path = Path()
            var started = false
            values.forEachIndexed { i, v ->
                if (v == null) {
                    started = false
                    return@forEachIndexed
                }
                val x = padX + i * slot + slot / 2f
                val y = yOf(v.toFloat())
                if (!started) {
                    path.moveTo(x, y)
                    started = true
                } else {
                    path.lineTo(x, y)
                }
            }
            drawPath(path, spec.color, style = Stroke(width = 2.2f, cap = StrokeCap.Round))
        }
    }
}

private fun sma(values: List<Double>, period: Int): List<Double?> {
    val out = MutableList<Double?>(values.size) { null }
    if (period <= 0 || values.size < period) return out
    var sum = 0.0
    for (i in values.indices) {
        sum += values[i]
        if (i >= period) sum -= values[i - period]
        if (i >= period - 1) out[i] = sum / period
    }
    return out
}
