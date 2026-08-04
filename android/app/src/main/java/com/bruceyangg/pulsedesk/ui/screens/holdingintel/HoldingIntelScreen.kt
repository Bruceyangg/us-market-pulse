package com.bruceyangg.pulsedesk.ui.screens.holdingintel

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.bruceyangg.pulsedesk.ui.components.ErrorState
import com.bruceyangg.pulsedesk.ui.components.LoadingState
import com.bruceyangg.pulsedesk.ui.components.PulseCard
import com.bruceyangg.pulsedesk.ui.components.ScreenHeader
import com.bruceyangg.pulsedesk.ui.theme.TapeDown
import com.bruceyangg.pulsedesk.ui.theme.TapeUp
import com.bruceyangg.pulsedesk.viewmodel.HoldingIntelViewModel

@Composable
fun HoldingIntelScreen(vm: HoldingIntelViewModel = viewModel()) {
    val state by vm.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    LaunchedEffect(Unit) { if (state.data == null) vm.load() }

    Column(Modifier.fillMaxSize()) {
        ScreenHeader(
            title = "持仓情报",
            subtitle = when {
                state.needsLogin -> "未登录 · 持仓需登录后查看"
                state.data != null -> "关联持仓的近端情报 · ${state.data?.count ?: 0} 条"
                else -> "按持仓代码匹配的情报流"
            },
            onRefresh = { vm.load(true) },
            refreshing = state.refreshing,
        )

        when {
            state.loading && state.data == null -> LoadingState()
            state.needsLogin -> ErrorState("持仓情报需先登录网页账户。\n当前原生端暂未接登录，请先在网站登录并添加持仓。") {
                vm.load(true)
            }
            state.error != null && state.data == null -> ErrorState(state.error!!) { vm.load(true) }
            else -> {
                val data = state.data ?: return@Column
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    if (data.symbols.isNotEmpty()) {
                        item {
                            Row(
                                Modifier.horizontalScroll(rememberScrollState()),
                                horizontalArrangement = Arrangement.spacedBy(8.dp),
                            ) {
                                FilterChip(
                                    selected = data.selected.isNullOrBlank(),
                                    onClick = { vm.selectSymbol(null) },
                                    label = { Text("全部 ${data.total}") },
                                )
                                data.symbols.forEach { sym ->
                                    FilterChip(
                                        selected = data.selected == sym.symbol,
                                        onClick = { vm.selectSymbol(sym.symbol) },
                                        label = { Text("${sym.symbol} ${sym.count}") },
                                    )
                                }
                            }
                        }
                    }
                    if (data.items.isEmpty()) {
                        item {
                            Text(
                                "暂无与持仓匹配的情报。添加持仓或稍后再刷新。",
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                    }
                    items(data.items, key = { it.id ?: it.url ?: it.title.orEmpty() }) { item ->
                        PulseCard {
                            Column(
                                Modifier
                                    .fillMaxWidth()
                                    .clickable(enabled = !item.url.isNullOrBlank()) {
                                        item.url?.let {
                                            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(it)))
                                        }
                                    }
                                    .padding(14.dp),
                            ) {
                                Row(
                                    Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                ) {
                                    Text(
                                        (item.holding_matches ?: emptyList()).joinToString(" · ")
                                            .ifBlank { item.source ?: "情报" },
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
                                item.summary_zh?.let {
                                    Text(
                                        it,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        style = MaterialTheme.typography.bodyMedium,
                                        modifier = Modifier.padding(top = 6.dp),
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
