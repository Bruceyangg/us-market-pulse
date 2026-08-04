package com.bruceyangg.pulsedesk.ui.screens.portfolio

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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
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
import com.bruceyangg.pulsedesk.viewmodel.PortfolioViewModel

@Composable
fun PortfolioScreen(vm: PortfolioViewModel = viewModel()) {
    val state by vm.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { if (state.data == null) vm.load() }

    Column(Modifier.fillMaxSize()) {
        ScreenHeader(
            title = "持仓",
            subtitle = state.data?.note ?: "同步网页端持仓（访客模式可能为空）",
            onRefresh = { vm.load(true) },
            refreshing = state.refreshing,
        )
        when {
            state.loading && state.data == null -> LoadingState()
            state.error != null && state.data == null -> ErrorState(state.error!!) { vm.load(true) }
            else -> {
                val data = state.data
                if (data == null || data.holdings.isEmpty()) {
                    ErrorState("还没有持仓。请先在网页端登录并添加美股代码。") { vm.load(true) }
                    return@Column
                }
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    data.board?.let { board ->
                        item {
                            PulseCard {
                                Column(Modifier.padding(14.dp)) {
                                    Row(
                                        Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                    ) {
                                        Text(
                                            "${board.name ?: board.label ?: board.symbol} · ${board.symbol}",
                                            fontWeight = FontWeight.Bold,
                                        )
                                        PctBadge(board.change_pct)
                                    }
                                    Spacer(Modifier.height(8.dp))
                                    val series = board.series[vm.timeframe]
                                    CandleChart(
                                        points = series?.points ?: board.points,
                                        showMa = vm.timeframe != "intraday",
                                        lineMode = series?.chart == "line" || vm.timeframe == "intraday",
                                    )
                                }
                            }
                        }
                    }
                    items(data.holdings, key = { it.symbol }) { h ->
                        PulseCard {
                            Row(
                                Modifier
                                    .fillMaxWidth()
                                    .padding(14.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Column {
                                    Text(h.name ?: h.label ?: h.symbol, fontWeight = FontWeight.SemiBold)
                                    Text(h.symbol, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                                Column(horizontalAlignment = Alignment.End) {
                                    Text(
                                        priceText(h.price),
                                        fontWeight = FontWeight.Bold,
                                        color = tapeColor(h.change_pct),
                                    )
                                    PctBadge(h.change_pct)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
