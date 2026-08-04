package com.bruceyangg.pulsedesk.data.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonElement

@Serializable
data class MarketsResponse(
    val indices: List<IndexCard> = emptyList(),
    val charts: List<MarketChart> = emptyList(),
    val charts_by_tf: Map<String, List<MarketChart>> = emptyMap(),
    val timeframes: List<Timeframe> = emptyList(),
    val default_tf: String? = null,
    val fetched_at: Double? = null,
    val cached: Boolean? = null,
    val errors: List<String> = emptyList(),
)

@Serializable
data class IndexCard(
    val id: String? = null,
    val symbol: String? = null,
    val label: String? = null,
    val short: String? = null,
    val price: Double? = null,
    val change: Double? = null,
    val change_pct: Double? = null,
    val unit: String? = null,
    val points: List<ChartPoint> = emptyList(),
)

@Serializable
data class MarketChart(
    val id: String? = null,
    val label: String? = null,
    val short: String? = null,
    val change_pct: Double? = null,
    val chart: String? = null,
    val blurb: String? = null,
    val points: List<ChartPoint> = emptyList(),
)

@Serializable
data class ChartPoint(
    val t: Long? = null,
    val v: Double? = null,
    val o: Double? = null,
    val h: Double? = null,
    val l: Double? = null,
    val c: Double? = null,
)

@Serializable
data class Timeframe(
    val id: String,
    val label: String,
    val blurb: String? = null,
    val chart: String? = null,
)

@Serializable
data class SectorsResponse(
    val sectors: List<SectorEtf> = emptyList(),
    val hot_sectors: List<SectorEtf> = emptyList(),
    val active_sector_id: String? = null,
    val picks: List<SectorPick> = emptyList(),
    val selected_symbol: String? = null,
    val selected_pick: SectorPick? = null,
    val value_chain: ValueChain? = null,
    val timeframes: List<Timeframe> = emptyList(),
    val fetched_at: Double? = null,
    val cached: Boolean? = null,
)

@Serializable
data class SectorEtf(
    val id: String,
    val symbol: String? = null,
    val label: String,
    val short: String? = null,
    val change_pct: Double? = null,
    val month_change_pct: Double? = null,
    val is_hot: Boolean? = null,
    val is_wave: Boolean? = null,
    val points: List<ChartPoint> = emptyList(),
)

@Serializable
data class SectorPick(
    val symbol: String,
    val name: String? = null,
    val price: Double? = null,
    val change_pct: Double? = null,
    val month_change_pct: Double? = null,
    val is_wave: Boolean? = null,
    val sector_id: String? = null,
    val sector_label: String? = null,
    val series: Map<String, SeriesBundle> = emptyMap(),
    val move_analysis: MoveAnalysis? = null,
    val value_chain: ValueChain? = null,
)

@Serializable
data class SeriesBundle(
    val chart: String? = null,
    val change_pct: Double? = null,
    val blurb: String? = null,
    val points: List<ChartPoint> = emptyList(),
)

@Serializable
data class MoveAnalysis(
    val summary: String? = null,
    val factors: List<String> = emptyList(),
)

@Serializable
data class ValueChain(
    val name: String? = null,
    val business: String? = null,
    val industry: String? = null,
    val chain_position: String? = null,
    val upstream: List<String> = emptyList(),
    val downstream: List<String> = emptyList(),
    val bear_risks: List<String> = emptyList(),
)

@Serializable
data class SectorMapResponse(
    val sectors: List<MapSector> = emptyList(),
    val stats: MapStats? = null,
    val cached: Boolean? = null,
    val source: String? = null,
)

@Serializable
data class MapStats(
    val symbols: Int? = null,
    val quoted: Int? = null,
    val up: Int? = null,
    val down: Int? = null,
    val flat: Int? = null,
)

@Serializable
data class MapSector(
    val id: String,
    val label: String,
    val desk_id: String? = null,
    val weight: Double? = null,
    val change_pct: Double? = null,
    val groups: List<MapGroup> = emptyList(),
)

@Serializable
data class MapGroup(
    val id: String,
    val label: String,
    val weight: Double? = null,
    val change_pct: Double? = null,
    val children: List<MapStock> = emptyList(),
)

@Serializable
data class MapStock(
    val symbol: String,
    val name: String? = null,
    val weight: Double? = null,
    val change_pct: Double? = null,
    val price: Double? = null,
)

@Serializable
data class EarningsResponse(
    val dates: List<EarningsDate> = emptyList(),
    val focus: List<EarningsRow> = emptyList(),
    val rows: List<EarningsRow> = emptyList(),
    val selected_date: String? = null,
    val fetched_at: Double? = null,
    val cached: Boolean? = null,
)

@Serializable
data class EarningsDate(
    val date: String,
    val label: String? = null,
    val count: Int? = null,
)

@Serializable
data class EarningsRow(
    val symbol: String? = null,
    val name: String? = null,
    val date: String? = null,
    val time: String? = null,
    val session: String? = null,
    val market_cap: String? = null,
    val eps_estimate: Double? = null,
    val eps_actual: Double? = null,
    val is_focus: Boolean? = null,
    val surprise_pct: Double? = null,
)

@Serializable
data class IntelResponse(
    val items: List<IntelItem> = emptyList(),
    val mood: MoodSummary? = null,
    val fetched_at: Double? = null,
    val cached: Boolean? = null,
)

@Serializable
data class IntelItem(
    val id: String? = null,
    val title: String? = null,
    val summary_zh: String? = null,
    val source: String? = null,
    val url: String? = null,
    val published_at: Double? = null,
    val sentiment: String? = null,
    val score: Double? = null,
    val category: String? = null,
)

@Serializable
data class MoodSummary(
    val label: String? = null,
    val blurb: String? = null,
    val score: Double? = null,
)

@Serializable
data class PortfolioResponse(
    val holdings: List<Holding> = emptyList(),
    val selected: String? = null,
    val board: Holding? = null,
    val note: String? = null,
    val max_holdings: Int? = null,
    val timeframes: List<Timeframe> = emptyList(),
    val default_tf: String? = null,
)

@Serializable
data class Holding(
    val symbol: String,
    val name: String? = null,
    val label: String? = null,
    val price: Double? = null,
    val change_pct: Double? = null,
    val series: Map<String, SeriesBundle> = emptyMap(),
    val points: List<ChartPoint> = emptyList(),
)

@Serializable
data class HealthResponse(
    val ok: Boolean? = null,
    val status: String? = null,
)

/** Loose decode helper for unexpected nested payloads. */
@Serializable
data class JsonBag(val raw: JsonElement? = null)
