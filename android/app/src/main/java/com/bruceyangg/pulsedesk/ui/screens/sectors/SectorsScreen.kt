package com.bruceyangg.pulsedesk.ui.screens.sectors

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
import com.bruceyangg.pulsedesk.ui.components.SectorTreemap
import com.bruceyangg.pulsedesk.ui.components.WaveChip
import com.bruceyangg.pulsedesk.ui.components.priceText
import com.bruceyangg.pulsedesk.ui.theme.tapeColor
import com.bruceyangg.pulsedesk.viewmodel.SectorsViewModel

@Composable
fun SectorsScreen(vm: SectorsViewModel = viewModel()) {
    val deskState by vm.desk.collectAsStateWithLifecycle()
    val mapState by vm.map.collectAsStateWithLifecycle()
    LaunchedEffect(Unit) {
        if (deskState.data == null) vm.load()
    }

    Column(Modifier.fillMaxSize()) {
        ScreenHeader(
            title = "板块",
            subtitle = mapState.data?.stats?.let {
                "涨跌图 ${it.quoted ?: 0}/${it.symbols ?: 0} · 涨 ${it.up ?: 0} 跌 ${it.down ?: 0}"
            } ?: "全板块涨跌图 · 热点板块 · 个股下钻",
            onRefresh = { vm.load(force = true) },
            refreshing = deskState.refreshing || mapState.refreshing,
        )

        when {
            deskState.loading && deskState.data == null -> LoadingState("加载板块台…")
            deskState.error != null && deskState.data == null ->
                ErrorState(deskState.error!!) { vm.load(true) }
            else -> {
                val desk = deskState.data ?: return@Column
                LazyColumn(
                    contentPadding = PaddingValues(bottom = 24.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    item {
                        Text(
                            "全板块涨跌图",
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.padding(horizontal = 16.dp),
                        )
                        Text(
                            "点色块下钻个股 · 点板块标题切换热点池",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            style = MaterialTheme.typography.bodyMedium,
                            modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
                        )
                        when {
                            mapState.loading && mapState.data == null -> {
                                LoadingState("拉取全板块行情…")
                            }
                            mapState.error != null && mapState.data == null -> {
                                Text(
                                    mapState.error!!,
                                    color = MaterialTheme.colorScheme.error,
                                    modifier = Modifier.padding(16.dp),
                                )
                            }
                            else -> {
                                val map = mapState.data
                                if (map != null && map.sectors.isNotEmpty()) {
                                    SectorTreemap(
                                        sectors = map.sectors,
                                        modifier = Modifier.padding(horizontal = 12.dp),
                                        onSectorClick = { vm.selectSector(it) },
                                        onStockClick = { sym, deskId -> vm.selectSymbol(sym, deskId) },
                                    )
                                }
                            }
                        }
                    }

                    item {
                        Text(
                            "热点板块",
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
                        )
                    }
                    item {
                        Row(
                            Modifier
                                .horizontalScroll(rememberScrollState())
                                .padding(horizontal = 12.dp),
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                        ) {
                            desk.sectors.forEach { sec ->
                                FilterChip(
                                    selected = sec.id == desk.active_sector_id,
                                    onClick = { vm.selectSector(sec.id) },
                                    label = {
                                        Text("${sec.label} ${com.bruceyangg.pulsedesk.ui.components.pctText(sec.change_pct)}")
                                    },
                                )
                            }
                        }
                    }

                    item {
                        val pick = desk.selected_pick
                        if (pick != null) {
                            PulseCard(Modifier.padding(horizontal = 16.dp)) {
                                Column(Modifier.padding(14.dp)) {
                                    Row(
                                        Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically,
                                    ) {
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                                        ) {
                                            Text(
                                                "${pick.name ?: pick.symbol} · ${pick.symbol}",
                                                fontWeight = FontWeight.Bold,
                                                style = MaterialTheme.typography.titleMedium,
                                            )
                                            WaveChip(pick.is_wave == true)
                                        }
                                        PctBadge(pick.change_pct)
                                    }
                                    Text(
                                        "现价 ${priceText(pick.price)} · ${pick.sector_label ?: ""}",
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        modifier = Modifier.padding(top = 4.dp),
                                    )
                                    Row(
                                        Modifier
                                            .horizontalScroll(rememberScrollState())
                                            .padding(vertical = 8.dp),
                                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                                    ) {
                                        desk.timeframes.forEach { tf ->
                                            FilterChip(
                                                selected = vm.timeframe == tf.id,
                                                onClick = { vm.setTimeframe(tf.id) },
                                                label = { Text(tf.label) },
                                            )
                                        }
                                    }
                                    val series = pick.series[vm.timeframe]
                                    CandleChart(
                                        points = series?.points ?: emptyList(),
                                        showMa = vm.timeframe != "intraday",
                                        lineMode = series?.chart == "line" || vm.timeframe == "intraday",
                                    )
                                    pick.move_analysis?.summary?.let {
                                        Text(
                                            it,
                                            style = MaterialTheme.typography.bodyMedium,
                                            modifier = Modifier.padding(top = 10.dp),
                                        )
                                    }
                                    pick.value_chain?.business?.let {
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

                    item {
                        Text(
                            "一轮涨势",
                            style = MaterialTheme.typography.titleMedium,
                            modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
                        )
                    }
                    items(desk.picks, key = { it.symbol }) { pick ->
                        PulseCard(Modifier.padding(horizontal = 16.dp)) {
                            Row(
                                Modifier
                                    .fillMaxWidth()
                                    .clickable { vm.selectSymbol(pick.symbol, pick.sector_id) }
                                    .padding(14.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Column(Modifier.weight(1f)) {
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                                    ) {
                                        Text(pick.name ?: pick.symbol, fontWeight = FontWeight.SemiBold)
                                        WaveChip(pick.is_wave == true)
                                    }
                                    Text(
                                        pick.symbol,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    )
                                }
                                Column(horizontalAlignment = Alignment.End) {
                                    Text(
                                        priceText(pick.price),
                                        fontWeight = FontWeight.Bold,
                                        color = tapeColor(pick.change_pct),
                                    )
                                    PctBadge(pick.month_change_pct ?: pick.change_pct)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
