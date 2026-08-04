package com.bruceyangg.pulsedesk.ui.screens.intel

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.clickable
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
import com.bruceyangg.pulsedesk.viewmodel.IntelViewModel

@Composable
fun IntelScreen(vm: IntelViewModel = viewModel()) {
    val state by vm.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    LaunchedEffect(Unit) { if (state.data == null) vm.load() }

    Column(Modifier.fillMaxSize()) {
        ScreenHeader(
            title = "情报",
            subtitle = state.data?.mood?.blurb ?: "美股相关公开情报流",
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
                    data.mood?.label?.let {
                        item {
                            PulseCard {
                                Column(Modifier.padding(14.dp)) {
                                    Text("近端情绪", style = MaterialTheme.typography.titleMedium)
                                    Text(it, fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 4.dp))
                                    data.mood.blurb?.let { blurb ->
                                        Text(
                                            blurb,
                                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                                            modifier = Modifier.padding(top = 4.dp),
                                        )
                                    }
                                }
                            }
                        }
                    }
                    items(data.items, key = { it.id ?: it.url ?: it.title.orEmpty() }) { item ->
                        PulseCard {
                            Column(
                                Modifier
                                    .fillMaxWidth()
                                    .clickable(enabled = !item.url.isNullOrBlank()) {
                                        item.url?.let { url ->
                                            context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                                        }
                                    }
                                    .padding(14.dp),
                            ) {
                                Row(
                                    Modifier.fillMaxWidth(),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                ) {
                                    Text(
                                        item.source ?: item.category ?: "情报",
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        style = MaterialTheme.typography.labelLarge,
                                    )
                                    val sent = item.sentiment
                                    Text(
                                        when (sent) {
                                            "bullish" -> "偏多"
                                            "bearish" -> "偏空"
                                            else -> "中性"
                                        },
                                        color = when (sent) {
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
                                        modifier = Modifier.padding(top = 6.dp),
                                        style = MaterialTheme.typography.bodyMedium,
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
