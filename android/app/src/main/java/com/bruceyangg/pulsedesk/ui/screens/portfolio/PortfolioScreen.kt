package com.bruceyangg.pulsedesk.ui.screens.portfolio

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.clickable
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.bruceyangg.pulsedesk.data.model.Holding
import com.bruceyangg.pulsedesk.data.model.IntelItem
import com.bruceyangg.pulsedesk.data.model.StockEarnings
import com.bruceyangg.pulsedesk.data.model.ValueChain
import com.bruceyangg.pulsedesk.ui.components.CandleChart
import com.bruceyangg.pulsedesk.ui.components.ErrorState
import com.bruceyangg.pulsedesk.ui.components.LoadingState
import com.bruceyangg.pulsedesk.ui.components.PctBadge
import com.bruceyangg.pulsedesk.ui.components.PulseCard
import com.bruceyangg.pulsedesk.ui.components.ScreenHeader
import com.bruceyangg.pulsedesk.ui.components.priceText
import com.bruceyangg.pulsedesk.ui.theme.TapeDown
import com.bruceyangg.pulsedesk.ui.theme.TapeUp
import com.bruceyangg.pulsedesk.ui.theme.tapeColor
import com.bruceyangg.pulsedesk.viewmodel.AuthViewModel
import com.bruceyangg.pulsedesk.viewmodel.HoldingIntelViewModel
import com.bruceyangg.pulsedesk.viewmodel.PortfolioViewModel

@Composable
fun PortfolioScreen(
    vm: PortfolioViewModel = viewModel(),
    intelVm: HoldingIntelViewModel = viewModel(),
    authVm: AuthViewModel = viewModel(),
    onLoginClick: () -> Unit = {},
) {
    val state by vm.state.collectAsStateWithLifecycle()
    val intelState by intelVm.state.collectAsStateWithLifecycle()
    val auth by authVm.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    LaunchedEffect(Unit) {
        if (state.data == null) vm.load()
        if (intelState.data == null) intelVm.load()
    }
    LaunchedEffect(auth.authenticated, auth.bootstrapped) {
        if (!auth.bootstrapped) return@LaunchedEffect
        vm.load(true)
        intelVm.load(true)
    }

    Column(Modifier.fillMaxSize()) {
        ScreenHeader(
            title = "持仓",
            subtitle = when {
                state.needsLogin -> "未登录 · 登录后查看与管理个人持仓"
                else -> state.data?.note ?: "自定义股票 · 云端同步 · 红涨绿跌"
            },
            onRefresh = { vm.load(true) },
            refreshing = state.refreshing,
        )
        when {
            state.loading && state.data == null -> LoadingState()
            state.needsLogin -> ErrorState(
                message = "未登录 · 持仓需登录后查看\n可在本机注册账户，与网页端同步。",
                actionLabel = "登录 / 注册",
                onAction = onLoginClick,
                onRetry = { vm.load(true) },
            )
            state.error != null && state.data == null -> ErrorState(state.error!!) { vm.load(true) }
            else -> {
                val data = state.data
                if (data == null || data.holdings.isEmpty()) {
                    ErrorState("还没有持仓。登录后请先在网页端或后续版本添加美股代码。") {
                        vm.load(true)
                    }
                    return@Column
                }
                val focus = data.focusHolding()
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    item {
                        Row(
                            Modifier
                                .horizontalScroll(rememberScrollState())
                                .padding(bottom = 4.dp),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            data.timeframes.ifEmpty {
                                listOf(
                                    com.bruceyangg.pulsedesk.data.model.Timeframe("intraday", "分时"),
                                    com.bruceyangg.pulsedesk.data.model.Timeframe("day", "日图"),
                                    com.bruceyangg.pulsedesk.data.model.Timeframe("month", "月图"),
                                    com.bruceyangg.pulsedesk.data.model.Timeframe("quarter", "季图"),
                                    com.bruceyangg.pulsedesk.data.model.Timeframe("year", "年图"),
                                )
                            }.forEach { tf ->
                                FilterChip(
                                    selected = vm.timeframe == tf.id,
                                    onClick = { vm.setTimeframe(tf.id) },
                                    label = { Text(tf.label) },
                                )
                            }
                        }
                    }

                    focus?.let { board ->
                        item {
                            FocusChartCard(board = board, timeframe = vm.timeframe)
                        }
                        item {
                            EarningsCard(
                                earn = data.selected_earnings ?: board.earnings,
                                holding = board,
                            )
                        }
                        item {
                            MoveAnalysisCard(board)
                        }
                        item {
                            ValueChainCard(data.value_chain ?: board.value_chain)
                        }
                    }

                    if (data.earnings_calendar.isNotEmpty()) {
                        item {
                            Text(
                                "临近财报",
                                style = MaterialTheme.typography.titleMedium,
                                modifier = Modifier.padding(top = 4.dp),
                            )
                        }
                        items(data.earnings_calendar.take(5), key = { it.symbol ?: it.next_earnings_label.orEmpty() }) { row ->
                            PulseCard {
                                Row(
                                    Modifier
                                        .fillMaxWidth()
                                        .padding(14.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                ) {
                                    Column {
                                        Text(row.symbol ?: "—", fontWeight = FontWeight.Bold)
                                        Text(
                                            row.name ?: "",
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        )
                                    }
                                    Text(
                                        when {
                                            row.days_to_earnings == null -> row.next_earnings_label ?: "—"
                                            row.days_to_earnings == 0 -> "今天"
                                            row.days_to_earnings!! > 0 -> "${row.days_to_earnings} 天后"
                                            else -> "已过 ${-row.days_to_earnings!!} 天"
                                        },
                                        fontWeight = FontWeight.SemiBold,
                                    )
                                }
                            }
                        }
                    }

                    item {
                        Text(
                            "持仓情报",
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.padding(top = 4.dp),
                        )
                    }
                    intelState.data?.let { intel ->
                        if (intel.symbols.isNotEmpty()) {
                            item {
                                Row(
                                    Modifier.horizontalScroll(rememberScrollState()),
                                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                                ) {
                                    FilterChip(
                                        selected = intel.selected.isNullOrBlank(),
                                        onClick = { intelVm.selectSymbol(null) },
                                        label = { Text("全部 ${intel.total ?: intel.count ?: 0}") },
                                    )
                                    intel.symbols.forEach { sym ->
                                        FilterChip(
                                            selected = intel.selected == sym.symbol,
                                            onClick = { intelVm.selectSymbol(sym.symbol) },
                                            label = { Text("${sym.symbol} ${sym.count ?: 0}") },
                                        )
                                    }
                                }
                            }
                        }
                        if (intel.items.isEmpty()) {
                            item {
                                Text(
                                    "暂无与持仓匹配的情报",
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                        } else {
                            items(
                                intel.items.take(8),
                                key = { it.id ?: it.url ?: it.title.orEmpty() },
                            ) { item ->
                                HoldingIntelCard(item) {
                                    item.url?.let {
                                        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(it)))
                                    }
                                }
                            }
                        }
                    } ?: item {
                        Text(
                            when {
                                intelState.needsLogin -> "登录后显示持仓情报"
                                intelState.error != null -> intelState.error!!
                                else -> "加载持仓情报…"
                            },
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }

                    item {
                        Text(
                            "我的持仓",
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.padding(top = 4.dp),
                        )
                    }
                    items(data.holdings, key = { it.symbol }) { h ->
                        val selected = h.symbol == (data.selected ?: data.selected_symbol)
                        PulseCard {
                            Row(
                                Modifier
                                    .fillMaxWidth()
                                    .clickable { vm.selectSymbol(h.symbol) }
                                    .padding(14.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Column {
                                    Text(
                                        h.name ?: h.label ?: h.symbol,
                                        fontWeight = if (selected) FontWeight.Bold else FontWeight.SemiBold,
                                    )
                                    Text(
                                        h.symbol + (h.sector_label?.let { " · $it" } ?: ""),
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
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

@Composable
private fun FocusChartCard(board: Holding, timeframe: String) {
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
            val series = board.series[timeframe]
            CandleChart(
                points = series?.points ?: board.points,
                showMa = timeframe != "intraday",
                lineMode = series?.chart == "line" || timeframe == "intraday",
            )
        }
    }
}

@Composable
private fun EarningsCard(earn: StockEarnings?, holding: Holding) {
    PulseCard {
        Column(Modifier.padding(14.dp)) {
            Text("个股财报", style = MaterialTheme.typography.titleMedium)
            if (earn == null || (
                    earn.next_earnings_label.isNullOrBlank() &&
                        earn.prev_earnings_label.isNullOrBlank() &&
                        earn.last_eps_actual == null &&
                        earn.expect_eps == null &&
                        earn.eps_avg == null
                    )
            ) {
                Text(
                    "暂无财报明细",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 6.dp),
                )
                return@Column
            }
            Text(
                "${holding.name ?: holding.symbol}",
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.padding(top = 6.dp),
            )
            Text(
                "下一发布日 ${earn.next_earnings_label ?: "待定"} · 上次 ${earn.prev_earnings_label ?: "—"}",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(top = 4.dp),
            )
            val expect = earn.expect_eps ?: earn.eps_avg
            if (expect != null || earn.last_eps_actual != null) {
                Text(
                    "预期 EPS ${expect?.let { "%.2f".format(it) } ?: "—"} · 上次实际 ${
                        earn.last_eps_actual?.let { "%.2f".format(it) } ?: "—"
                    }",
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
        }
    }
}

@Composable
private fun MoveAnalysisCard(holding: Holding) {
    val analysis = holding.move_analysis ?: return
    PulseCard {
        Column(Modifier.padding(14.dp)) {
            Text("涨跌解读", style = MaterialTheme.typography.titleMedium)
            analysis.summary?.let {
                Text(it, modifier = Modifier.padding(top = 6.dp))
            }
            analysis.factors.take(4).forEach { factor ->
                Text(
                    "· $factor",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(top = 3.dp),
                )
            }
        }
    }
}

@Composable
private fun ValueChainCard(vc: ValueChain?) {
    if (vc == null) return
    PulseCard {
        Column(Modifier.padding(14.dp)) {
            Text("业务与产业链", style = MaterialTheme.typography.titleMedium)
            vc.business?.let {
                Text(it, modifier = Modifier.padding(top = 6.dp))
            }
            val loc = listOfNotNull(vc.industry, vc.chain_position).joinToString(" · ")
            if (loc.isNotBlank()) {
                Text(
                    loc,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
        }
    }
}

@Composable
private fun HoldingIntelCard(item: IntelItem, onOpen: () -> Unit) {
    PulseCard {
        Column(
            Modifier
                .fillMaxWidth()
                .clickable(enabled = !item.url.isNullOrBlank(), onClick = onOpen)
                .padding(14.dp),
        ) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Text(
                    (item.holding_matches).joinToString(" · ").ifBlank { item.source ?: "情报" },
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.labelLarge,
                )
                Text(
                    when (item.sentiment) {
                        "bullish" -> "偏多"
                        "bearish" -> "偏空"
                        else -> "中性"
                    },
                    color = when (item.sentiment) {
                        "bullish" -> TapeUp
                        "bearish" -> TapeDown
                        else -> MaterialTheme.colorScheme.onSurfaceVariant
                    },
                    fontWeight = FontWeight.SemiBold,
                )
            }
            Text(
                item.title ?: "无标题",
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.padding(top = 6.dp),
            )
            item.summary_zh?.takeIf { it.isNotBlank() }?.let {
                Text(
                    it,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.bodyMedium,
                    modifier = Modifier.padding(top = 4.dp),
                )
            }
        }
    }
}
