package com.bruceyangg.pulsedesk.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.bruceyangg.pulsedesk.data.model.MapSector
import com.bruceyangg.pulsedesk.data.model.MapStock
import com.bruceyangg.pulsedesk.ui.theme.heatColor

private data class Node(val value: Float, val payload: Any)
private data class Rect(val x: Float, val y: Float, val w: Float, val h: Float, val payload: Any)

private fun layoutTreemap(nodes: List<Node>, x: Float, y: Float, w: Float, h: Float, out: MutableList<Rect>) {
    val items = nodes.filter { it.value > 0f }
    if (items.isEmpty() || w < 1f || h < 1f) return
    if (items.size == 1) {
        out += Rect(x, y, w, h, items[0].payload)
        return
    }
    val total = items.sumOf { it.value.toDouble() }.toFloat().coerceAtLeast(1f)
    var acc = 0f
    var split = 1
    for (i in items.indices) {
        acc += items[i].value
        if (acc >= total * 0.5f) {
            split = (i + 1).coerceIn(1, items.lastIndex)
            break
        }
    }
    val left = items.take(split)
    val right = items.drop(split)
    val leftSum = left.sumOf { it.value.toDouble() }.toFloat()
    val ratio = leftSum / total
    if (w >= h) {
        val lw = w * ratio
        layoutTreemap(left, x, y, lw, h, out)
        layoutTreemap(right, x + lw, y, w - lw, h, out)
    } else {
        val lh = h * ratio
        layoutTreemap(left, x, y, w, lh, out)
        layoutTreemap(right, x, y + lh, w, h - lh, out)
    }
}

@Composable
fun SectorTreemap(
    sectors: List<MapSector>,
    modifier: Modifier = Modifier,
    onSectorClick: (deskId: String) -> Unit,
    onStockClick: (symbol: String, deskId: String) -> Unit,
) {
    BoxWithConstraints(
        modifier = modifier
            .fillMaxWidth()
            .height(360.dp)
            .clip(RoundedCornerShape(14.dp))
            .background(Color(0xFF121820))
            .border(1.dp, MaterialTheme.colorScheme.outline.copy(alpha = 0.5f), RoundedCornerShape(14.dp)),
    ) {
        val widthPx = constraints.maxWidth.toFloat().coerceAtLeast(1f)
        val heightPx = constraints.maxHeight.toFloat().coerceAtLeast(1f)
        val density = androidx.compose.ui.platform.LocalDensity.current

        val sectorRects = remember(sectors, widthPx, heightPx) {
            val nodes = sectors.map {
                Node(maxOf(0.5f, (it.weight ?: 1.0).toFloat()), it)
            }
            val out = mutableListOf<Rect>()
            layoutTreemap(nodes, 0f, 0f, widthPx, heightPx, out)
            out
        }

        sectorRects.forEach { secRect ->
            val sector = secRect.payload as MapSector
            val deskId = sector.desk_id ?: sector.id
            val gap = 2f
            val sx = secRect.x + gap
            val sy = secRect.y + gap
            val sw = (secRect.w - gap * 2).coerceAtLeast(1f)
            val sh = (secRect.h - gap * 2).coerceAtLeast(1f)
            val showHead = sh > 70f && sw > 80f
            val head = if (showHead) 28f else 0f
            val innerW = (sw - 2f).coerceAtLeast(1f)
            val innerH = (sh - head - 2f).coerceAtLeast(1f)

            val groupRects = remember(sector, innerW, innerH) {
                val nodes = sector.groups.map {
                    Node(maxOf(0.4f, (it.weight ?: 1.0).toFloat()), it)
                }
                val out = mutableListOf<Rect>()
                layoutTreemap(nodes, 0f, 0f, innerW, innerH, out)
                out
            }

            with(density) {
                Box(
                    modifier = Modifier
                        .offset(sx.toDp(), sy.toDp())
                        .size(sw.toDp(), sh.toDp())
                        .background(heatColor(sector.change_pct))
                        .border(1.dp, Color.Black.copy(alpha = 0.35f)),
                ) {
                    if (showHead) {
                        Text(
                            text = "${sector.label} ${pctText(sector.change_pct)}",
                            color = Color.White,
                            fontSize = 11.sp,
                            fontWeight = FontWeight.Bold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier
                                .fillMaxWidth()
                                .background(Color(0xB80D1218))
                                .clickable { onSectorClick(deskId) }
                                .padding(horizontal = 4.dp, vertical = 4.dp),
                        )
                    }
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(top = head.toDp()),
                    ) {
                        groupRects.forEach { gRect ->
                            val group = gRect.payload as com.bruceyangg.pulsedesk.data.model.MapGroup
                            val showGHead = gRect.h > 48f && gRect.w > 56f
                            val gHead = if (showGHead) 18f else 0f
                            val bodyW = (gRect.w - 1f).coerceAtLeast(1f)
                            val bodyH = (gRect.h - gHead - 1f).coerceAtLeast(1f)
                            val stockRects = remember(group, bodyW, bodyH) {
                                val nodes = group.children.map {
                                    Node(maxOf(0.3f, (it.weight ?: 1.0).toFloat()), it)
                                }
                                val out = mutableListOf<Rect>()
                                layoutTreemap(nodes, 0f, 0f, bodyW, bodyH, out)
                                out
                            }
                            Box(
                                modifier = Modifier
                                    .offset(gRect.x.toDp(), gRect.y.toDp())
                                    .size(gRect.w.toDp(), gRect.h.toDp())
                                    .border(0.5.dp, Color.Black.copy(alpha = 0.25f)),
                            ) {
                                if (showGHead) {
                                    Text(
                                        text = group.label,
                                        color = Color.White.copy(alpha = 0.85f),
                                        fontSize = 9.sp,
                                        fontWeight = FontWeight.SemiBold,
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                        modifier = Modifier
                                            .fillMaxWidth()
                                            .background(Color(0x8A0B1016))
                                            .padding(horizontal = 3.dp, vertical = 2.dp),
                                    )
                                }
                                Box(Modifier.padding(top = gHead.toDp()).fillMaxSize()) {
                                    stockRects.forEach { sRect ->
                                        val stock = sRect.payload as MapStock
                                        val showName = sRect.w > 52f && sRect.h > 36f
                                        val showPct = sRect.w > 34f && sRect.h > 24f
                                        Column(
                                            modifier = Modifier
                                                .offset(sRect.x.toDp(), sRect.y.toDp())
                                                .size(
                                                    (sRect.w - 0.8f).coerceAtLeast(1f).toDp(),
                                                    (sRect.h - 0.8f).coerceAtLeast(1f).toDp(),
                                                )
                                                .background(heatColor(stock.change_pct))
                                                .border(0.5.dp, Color.Black.copy(alpha = 0.2f))
                                                .clickable { onStockClick(stock.symbol, deskId) }
                                                .padding(3.dp),
                                            horizontalAlignment = Alignment.Start,
                                        ) {
                                            Text(
                                                stock.symbol,
                                                color = Color.White,
                                                fontSize = 10.sp,
                                                fontWeight = FontWeight.ExtraBold,
                                                maxLines = 1,
                                            )
                                            if (showName) {
                                                Text(
                                                    stock.name ?: "",
                                                    color = Color.White.copy(0.88f),
                                                    fontSize = 8.sp,
                                                    maxLines = 1,
                                                    overflow = TextOverflow.Ellipsis,
                                                )
                                            }
                                            if (showPct) {
                                                Text(
                                                    pctText(stock.change_pct),
                                                    color = Color.White,
                                                    fontSize = 9.sp,
                                                    fontWeight = FontWeight.Bold,
                                                )
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
