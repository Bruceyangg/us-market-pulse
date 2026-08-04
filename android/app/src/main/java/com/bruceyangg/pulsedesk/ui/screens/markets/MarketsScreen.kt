package com.bruceyangg.pulsedesk.ui.screens.markets

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.bruceyangg.pulsedesk.ui.components.CandleChart
import com.bruceyangg.pulsedesk.ui.components.ErrorState
import com.bruceyangg.pulsedesk.ui.components.LoadingState
import com.bruceyangg.pulsedesk.ui.components.PctBadge
import com.bruceyangg.pulsedesk.ui.components.PulseCard
import com.bruceyangg.pulsedesk.ui.components.ScreenHeader
import com.bruceyangg.pulsedesk.ui.components.priceText
import com.bruceyangg.pulsedesk.ui.theme.tapeColor
import com.bruceyangg.pulsedesk.viewmodel.MarketsViewModel

@Composable
fun MarketsScreen(vm: MarketsViewModel = viewModel()) {
    val state by vm.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { if (state.data == null) vm.load() }

    Column(Modifier.fillMaxSize()) {
        ScreenHeader(
            title = "市场",
            subtitle = when {
                state.refreshing -> "同步指数与 K 线…"
                state.data?.cached == true -> "已缓存 · 捏合缩放日图"
                else -> "美股指数 · 红涨绿跌 · 支持捏合缩放"
            },
            onRefresh = { vm.load(force = true) },
            refreshing = state.refreshing,
        )

        when {
            state.loading && state.data == null -> LoadingState("连接行情服务…\n冷启动可能需要十几秒")
            state.error != null && state.data == null -> ErrorState(state.error!!) { vm.load(true) }
            else -> {
                val data = state.data ?: return@Column
                val tfs = data.timeframes.ifEmpty {
                    listOf(
                        com.bruceyangg.pulsedesk.data.model.Timeframe("intraday", "分时"),
                        com.bruceyangg.pulsedesk.data.model.Timeframe("day", "日图"),
                        com.bruceyangg.pulsedesk.data.model.Timeframe("month", "月图"),
                        com.bruceyangg.pulsedesk.data.model.Timeframe("year", "年图"),
                    )
                }
                Row(
                    Modifier
                        .horizontalScroll(rememberScrollState())
                        .padding(horizontal = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    tfs.forEach { tf ->
                        FilterChip(
                            selected = vm.timeframe == tf.id,
                            onClick = { vm.setTimeframe(tf.id) },
                            label = { Text(tf.label) },
                        )
                    }
                }
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item {
                        Text("主要指数", style = MaterialTheme.typography.titleMedium)
                    }
                    items(data.indices, key = { it.id ?: it.symbol ?: it.label.orEmpty() }) { idx ->
                        PulseCard {
                            Column(Modifier.padding(14.dp)) {
                                Row(
                                    Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                ) {
                                    Column {
                                        Text(idx.label ?: idx.short ?: "—", fontWeight = FontWeight.SemiBold)
                                        Text(
                                            idx.symbol ?: "",
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                            style = MaterialTheme.typography.bodyMedium,
                                        )
                                    }
                                    Column(horizontalAlignment = androidx.compose.ui.Alignment.End) {
                                        Text(
                                            priceText(idx.price),
                                            fontWeight = FontWeight.Bold,
                                            color = tapeColor(idx.change_pct),
                                        )
                                        PctBadge(idx.change_pct)
                                    }
                                }
                                if (idx.points.size >= 2) {
                                    Spacer(Modifier.height(8.dp))
                                    CandleChart(
                                        points = idx.points,
                                        showMa = false,
                                        lineMode = true,
                                        modifier = Modifier.height(72.dp),
                                    )
                                }
                            }
                        }
                    }
                    val charts = data.charts_by_tf[vm.timeframe]
                        ?: data.charts_by_tf[data.default_tf]
                        ?: data.charts
                    if (charts.isNotEmpty()) {
                        item {
                            Spacer(Modifier.height(4.dp))
                            Text(
                                "走势图 · ${tfs.find { it.id == vm.timeframe }?.label ?: ""}",
                                style = MaterialTheme.typography.titleMedium,
                            )
                        }
                        items(charts, key = { it.id ?: it.label.orEmpty() }) { chart ->
                            PulseCard {
                                Column(Modifier.padding(14.dp)) {
                                    Row(
                                        Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                    ) {
                                        Text(chart.label ?: chart.short ?: "—", fontWeight = FontWeight.SemiBold)
                                        PctBadge(chart.change_pct)
                                    }
                                    if (!chart.blurb.isNullOrBlank()) {
                                        Text(
                                            chart.blurb,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                            style = MaterialTheme.typography.bodyMedium,
                                            modifier = Modifier.padding(top = 4.dp),
                                        )
                                    }
                                    Spacer(Modifier.height(8.dp))
                                    CandleChart(
                                        points = chart.points,
                                        showMa = vm.timeframe != "intraday",
                                        lineMode = chart.chart == "line" || vm.timeframe == "intraday",
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
