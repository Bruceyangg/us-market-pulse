package com.bruceyangg.pulsedesk.ui.screens.earnings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
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
import com.bruceyangg.pulsedesk.ui.components.ErrorState
import com.bruceyangg.pulsedesk.ui.components.LoadingState
import com.bruceyangg.pulsedesk.ui.components.PulseCard
import com.bruceyangg.pulsedesk.ui.components.ScreenHeader
import com.bruceyangg.pulsedesk.viewmodel.EarningsViewModel

@Composable
fun EarningsScreen(vm: EarningsViewModel = viewModel()) {
    val state by vm.state.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) { if (state.data == null) vm.load() }

    Column(Modifier.fillMaxSize()) {
        ScreenHeader(
            title = "财报",
            subtitle = "近一月美股财报日历 · 重点关注优先",
            onRefresh = { vm.load(true) },
            refreshing = state.refreshing,
        )
        when {
            state.loading && state.data == null -> LoadingState()
            state.error != null && state.data == null -> ErrorState(state.error!!) { vm.load(true) }
            else -> {
                val data = state.data ?: return@Column
                LazyColumn(
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    if (data.focus.isNotEmpty()) {
                        item {
                            Text("本月重点关注", style = MaterialTheme.typography.titleMedium)
                        }
                        items(data.focus, key = { "f-${it.symbol}-${it.date}" }) { row ->
                            EarningsCard(row, highlight = true)
                        }
                    }
                    item {
                        Text(
                            "全部日程 (${data.rows.size})",
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.padding(top = 8.dp),
                        )
                    }
                    items(data.rows, key = { "${it.symbol}-${it.date}-${it.time}" }) { row ->
                        EarningsCard(row, highlight = row.is_focus == true)
                    }
                }
            }
        }
    }
}

@Composable
private fun EarningsCard(
    row: com.bruceyangg.pulsedesk.data.model.EarningsRow,
    highlight: Boolean,
) {
    PulseCard {
        Column(Modifier.padding(14.dp)) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
            ) {
                Column {
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(row.symbol ?: "—", fontWeight = FontWeight.Bold)
                        if (highlight) {
                            Text(
                                "重点",
                                color = MaterialTheme.colorScheme.primary,
                                fontWeight = FontWeight.Bold,
                                style = MaterialTheme.typography.labelLarge,
                            )
                        }
                    }
                    Text(
                        row.name ?: "",
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
                Column(horizontalAlignment = androidx.compose.ui.Alignment.End) {
                    Text(row.date ?: "—", fontWeight = FontWeight.SemiBold)
                    Text(
                        listOfNotNull(row.session, row.time).joinToString(" · "),
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        style = MaterialTheme.typography.bodyMedium,
                    )
                }
            }
            if (!row.market_cap.isNullOrBlank()) {
                Text(
                    "市值 ${row.market_cap}",
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(top = 6.dp),
                    style = MaterialTheme.typography.bodyMedium,
                )
            }
        }
    }
}
